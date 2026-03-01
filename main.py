import requests
import os
import random
from yt_uploader import upload_to_youtube

def run_automation():
    # 1. Setup API Key
    api_key = input("Enter your Pollinations Secret Key (sk_...): ").strip()
    if not api_key:
        print("Error: API Key is required.")
        return

    topic = "Benefits of regular exercise"
    headers = {"Authorization": f"Bearer {api_key}"}

    # 2. Text Generation via gemini-search
    print("Generating text content via gemini-search...")
    text_url = "https://gen.pollinations.ai/v1/chat/completions"
    text_payload = {
        "model": "gemini-search",
        "messages": [
            {
                "role": "user", 
                "content": f"Write a professional social media post about {topic}. Include 3 key points and relevant hashtags. English only."
            }
        ]
    }

    try:
        res = requests.post(text_url, headers=headers, json=text_payload)
        res.raise_for_status()
        caption = res.json()['choices'][0]['message']['content']
        print("Text generated successfully.")
    except Exception as e:
        print(f"Text generation failed: {e}")
        return

    # 3. Video Generation with Fallback (Seedance -> Veo)
    video_filename = "output_video.mp4"
    video_prompt = f"Cinematic footage of a person jogging in a beautiful park, morning sunlight, 4k"
    encoded_prompt = requests.utils.quote(video_prompt)
    
    video_models = ["seedance", "veo"]
    success = False

    for model in video_models:
        print(f"Attempting to generate video using model: {model}")
        try:
            url = f"https://gen.pollinations.ai/image/{encoded_prompt}?model={model}"
            video_res = requests.get(url, headers=headers, timeout=120)
            video_res.raise_for_status()
            with open(video_filename, "wb") as f:
                f.write(video_res.content)
            print(f"Video generated successfully using {model}.")
            success = True
            break
        except Exception as e:
            print(f"Model {model} failed: {e}")

    # 4. Upload to YouTube if video exists
    if success and os.path.exists(video_filename):
        try:
            title = f"Health Tips: {topic}"
            upload_to_youtube(video_filename, title, caption)
        except Exception as e:
            print(f"YouTube upload failed: {e}")
    else:
        print("Process aborted: No video was generated.")

if __name__ == "__main__":
    run_automation()