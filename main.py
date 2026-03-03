import os
import re
import time
import subprocess
import requests
from urllib.parse import quote
from imageio_ffmpeg import get_ffmpeg_exe
from yt_uploader import upload_to_youtube  # 你原本的上載函式

TEXT_URL = "https://gen.pollinations.ai/v1/chat/completions"
IMAGE_GEN_BASE = "https://gen.pollinations.ai/image"  # 你的原端點
VIDEO_MODELS = ("grok-video", "veo")  # 先 seedance 再 veo

# ---- 可調參數 ----
EXACT_MATCH_PROMPT = False  # 若 True：影片 prompt 直接用 caption（容易 402，不建議）
FALLBACK_IMAGE_MODEL = "flux"  # 圖片模型（用來做 slideshow）
FALLBACK_IMAGES = 4           # 退回時生成的張數
PER_IMAGE_SEC = 3             # 每張圖片在影片的顯示秒數
OUT_VIDEO = "output_video.mp4"
# -------------------

def clean_text_basic(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[*_`~>#-]+", " ", text)  # 去 Markdown/符號
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text

def build_video_prompt_from_caption(caption: str, topic: str, max_len: int = 320) -> str:
    """
    把完整貼文 -> 視覺導向 prompt（主題、場景、主體、動作、光線/鏡頭）
    目的：既保持語意一致，又避免長文/符號觸發 402。
    """
    base = clean_text_basic(caption)
    first_sentence = re.split(r"[.!?]\s+", base, maxsplit=1)[0]
    core = first_sentence if len(first_sentence) >= 12 else (topic or "the topic")

    visual_prompt = (
        f"Cinematic b-roll illustrating: {core}. "
        "Show clear, concrete visuals (subject, environment, motion). "
        "Natural lighting, shallow depth of field, stable camera, 4k, high detail."
    )
    if len(visual_prompt) > max_len:
        visual_prompt = visual_prompt[:max_len].rsplit(" ", 1)[0] + "…"
    return visual_prompt

def try_generate_video(headers, prompt: str, filename: str, models=VIDEO_MODELS) -> bool:
    """
    嘗試多模型；遇到 402 會自動簡化 prompt + backoff 再試。
    成功會把內容存成 filename，並回傳 True。
    """
    cur_prompt = prompt
    for attempt in range(3):
        for model in models:
            print(f"Attempting to generate video using model: {model} (try {attempt+1})")
            try:
                url = f"{IMAGE_GEN_BASE}/{quote(cur_prompt)}?model={model}"
                res = requests.get(url, headers=headers, timeout=120)
                if res.status_code == 402:
                    print("402 Payment Required: likely quota/plan/prompt cost. Will simplify and retry.")
                    break  # 先離開內層循環，做 prompt 簡化與 backoff
                res.raise_for_status()
                with open(filename, "wb") as f:
                    f.write(res.content)
                print(f"Video generated successfully using {model}.")
                return True
            except Exception as e:
                print(f"Model {model} failed: {e}")

        # Prompt 降級：去怪符號 + 截短字數
        cur_prompt = re.sub(r"[^\w\s,.-]", " ", cur_prompt)
        words = cur_prompt.split()
        if len(words) > 50:
            cur_prompt = " ".join(words[:50]) + "…"
        time.sleep(5 * (attempt + 1))  # backoff
    return False

def images_to_video_ffmpeg(image_paths, out_video, fps=24, per_image_sec=3):
    """
    用 ffmpeg (透過 imageio-ffmpeg 取得 exe) 把多張圖片合成 MP4。
    使用 concat demuxer，每張圖用 duration 控制顯示秒數。
    """
    if not image_paths:
        raise RuntimeError("No images to build video.")

    ffmpeg = get_ffmpeg_exe()  # 由 imageio-ffmpeg 提供，首次可能會下載
    list_file = "frames.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in image_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
            f.write(f"duration {per_image_sec}\n")
        # concat 需要最後再重覆最後一張，確保總時長正確
        f.write(f"file '{os.path.abspath(image_paths[-1])}'\n")

    cmd = [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-vsync", "vfr",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-c:v", "libx264",
        out_video
    ]
    print("Running ffmpeg to create slideshow...")
    subprocess.check_call(cmd)
    os.remove(list_file)
    print("Slideshow video created via ffmpeg.")

def fallback_create_slideshow_from_images(headers, topic: str, out_video: str, num_images: int = 4, per_image_sec: float = 3.0) -> bool:
    """
    當影片生成失敗/402，多張圖片 + ffmpeg 合成簡易影片。
    """
    print("Falling back to image slideshow…")
    os.makedirs("tmp_frames", exist_ok=True)
    frame_paths = []

    for i in range(num_images):
        img_prompt = (
            f"High quality photo illustrating: {topic}. "
            f"Scene {i+1}, cinematic composition, natural light, 4k."
        )
        url = f"{IMAGE_GEN_BASE}/{quote(img_prompt)}?model={FALLBACK_IMAGE_MODEL}"
        try:
            res = requests.get(url, headers=headers, timeout=60)
            res.raise_for_status()
            frame_path = os.path.join("tmp_frames", f"frame_{i+1}.jpg")
            with open(frame_path, "wb") as f:
                f.write(res.content)
            frame_paths.append(frame_path)
            time.sleep(1.5)
        except Exception as e:
            print(f"Image {i+1} failed: {e}")

    if not frame_paths:
        print("No images generated for slideshow fallback.")
        return False

    try:
        images_to_video_ffmpeg(frame_paths, out_video, fps=24, per_image_sec=per_image_sec)
        # 清理臨時圖片（想保留就註解掉）
        for p in frame_paths:
            try:
                os.remove(p)
            except Exception:
                pass
        try:
            os.rmdir("tmp_frames")
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"Failed to create slideshow video: {e}")
        return False

def run_automation():
    # 1) API Key
    api_key = input("Enter your Pollinations Secret Key (sk_...): ").strip()
    if not api_key:
        print("Error: API Key is required.")
        return
    headers = {"Authorization": f"Bearer {api_key}"}

    # 2) Topic
    topic = input("Enter the topic for your post/video (e.g., 'Benefits of regular exercise'): ").strip()
    if not topic:
        print("Error: Topic is required.")
        return

    # 3) 產生貼文文字
    print("Generating text content via gemini-search...")
    text_payload = {
        "model": "gemini-search",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Write a professional social media post about {topic}. "
                    f"Include 3 key points and relevant hashtags. English only."
                )
            }
        ]
    }
    try:
        res = requests.post(TEXT_URL, headers=headers, json=text_payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        caption = (
            data.get('choices', [{}])[0]
                .get('message', {})
                .get('content', '')
        ).strip()
        if not caption:
            raise ValueError("Empty content returned by text generation API.")
        print("Text generated successfully.")
    except Exception as e:
        print(f"Text generation failed: {e}")
        return

    # 4) 構建影片 prompt（如要完全用 caption，改 EXACT_MATCH_PROMPT=True）
    if EXACT_MATCH_PROMPT:
        video_prompt = caption
    else:
        video_prompt = build_video_prompt_from_caption(caption, topic)

    # 5) 影片生成（有 402 自動降級）
    success = try_generate_video(headers, video_prompt, OUT_VIDEO)

    # 6) 不行就退回：多圖 + ffmpeg 合成影片
    if not success:
        success = fallback_create_slideshow_from_images(headers, topic, OUT_VIDEO, num_images=FALLBACK_IMAGES, per_image_sec=PER_IMAGE_SEC)

    # 7) 上載 YouTube
    if success and os.path.exists(OUT_VIDEO):
        try:
            title = f"{topic} | Auto Video"
            upload_to_youtube(OUT_VIDEO, title, caption)
            print("Upload to YouTube completed.")
        except Exception as e:
            print(f"YouTube upload failed: {e}")
    else:
        print("Process aborted: No video was generated.")

if __name__ == "__main__":
    run_automation()
