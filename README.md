
# 🤖 AI YouTube Automation Platform - Setup Guide

This platform uses **Pollinations.ai** (via `gemini-search` and `grok-video`/`veo`) to generate social-media captions and videos, then automatically uploads them to YouTube via the **YouTube Data API v3**.

---

## Table of Contents
1. [How It Works](#1-how-it-works)
2. [Code Reference](#2-code-reference)
3. [Prerequisites](#3-prerequisites)
4. [Google Cloud Platform Setup](#4-google-cloud-platform-gcp-setup)
5. [Local Environment Setup](#5-local-environment-setup)
6. [Running the Program](#6-running-the-program)
7. [Customization](#7-customization)
8. [Limitations & Troubleshooting](#8-limitations--troubleshooting)

---

## 1. How It Works

The automation runs as a single Python command and performs the following steps end-to-end:

```
python main.py
  │
  ├─ 1. Prompt for Pollinations API key & topic
  ├─ 2. Generate text caption  (gemini-search model)
  ├─ 3. Build a visual video prompt from the caption
  ├─ 4. Generate MP4 video    (grok-video → veo, with auto-retry)
  │       └─ Fallback: download 4 images → stitch into slideshow via ffmpeg
  └─ 5. Upload the MP4 to YouTube (YouTube Data API v3 / OAuth 2.0)
```

---

## 2. Code Reference

The project consists of two Python modules.

### `main.py` — Main Orchestration Script

#### Top-level constants (tunable parameters)

| Constant | Default | Description |
|---|---|---|
| `TEXT_URL` | Pollinations chat endpoint | REST endpoint used for text generation |
| `IMAGE_GEN_BASE` | Pollinations image/video endpoint | Base URL for image and video generation |
| `VIDEO_MODELS` | `("grok-video", "veo")` | Ordered list of video models to try; first model is tried first |
| `EXACT_MATCH_PROMPT` | `False` | If `True`, the raw caption is sent as the video prompt (may trigger 402 errors); `False` uses a condensed visual prompt |
| `FALLBACK_IMAGE_MODEL` | `"flux"` | Image model used when video generation fails entirely |
| `FALLBACK_IMAGES` | `4` | Number of still images to generate for the slideshow fallback |
| `PER_IMAGE_SEC` | `3` | Seconds each image is shown in the slideshow fallback |
| `OUT_VIDEO` | `"output_video.mp4"` | Filename of the generated/downloaded video |

#### Functions

| Function | Signature | Description |
|---|---|---|
| `clean_text_basic` | `(text: str) -> str` | Strips Markdown symbols and collapses whitespace from a string; used before building video prompts |
| `build_video_prompt_from_caption` | `(caption: str, topic: str, max_len: int = 320) -> str` | Converts a long social-media caption into a concise, cinematic video prompt (≤ `max_len` characters) |
| `try_generate_video` | `(headers, prompt: str, filename: str, models=VIDEO_MODELS) -> bool` | Iterates over `models`, retrying up to 3 times; simplifies the prompt on a 402 error; saves the video to `filename` and returns `True` on success |
| `images_to_video_ffmpeg` | `(image_paths, out_video, fps=24, per_image_sec=3)` | Uses **imageio-ffmpeg** to locate the bundled ffmpeg binary and runs the `concat` demuxer to stitch images into an MP4 |
| `fallback_create_slideshow_from_images` | `(headers, topic: str, out_video: str, num_images: int = 4, per_image_sec: float = 3.0) -> bool` | Downloads `num_images` still images from Pollinations, calls `images_to_video_ffmpeg`, cleans up temp files, and returns `True` on success |
| `run_automation` | `()` | Entry-point that orchestrates the full pipeline (steps 1–5 above); called by `if __name__ == "__main__"` |

---

### `yt_uploader.py` — YouTube Upload Module

#### Constants

| Constant | Value | Description |
|---|---|---|
| `SCOPES` | `['https://www.googleapis.com/auth/youtube.upload']` | OAuth 2.0 scope required to upload videos |

#### Functions

| Function | Signature | Description |
|---|---|---|
| `get_authenticated_service` | `() -> googleapiclient.discovery.Resource` | Loads saved credentials from `token.pickle`; if missing or expired it opens a local browser window for OAuth 2.0 consent; saves new credentials back to `token.pickle`; returns an authenticated YouTube API client |
| `upload_to_youtube` | `(file_path, title, description) -> str` | Calls the YouTube `videos.insert` API with the given file, title, and description; uses resumable chunked upload; prints the resulting video URL and returns the video ID |

#### Customisable upload settings (inside `upload_to_youtube`)

| Setting | Default | How to change |
|---|---|---|
| `privacyStatus` | `'public'` | Change to `'private'` or `'unlisted'` to review before publishing |
| `categoryId` | `'22'` (People & Blogs) | Change to `'27'` (Education) or `'28'` (Science & Tech) |
| `tags` | `['AI', 'Health', 'Automation']` | Replace with keywords relevant to your content for better SEO |

---

## 3. Prerequisites

*   **Python 3.10+** installed on your system ([python.org](https://www.python.org/downloads/)).
*   **Pollinations.ai Secret Key**: An API key starting with `sk_` — sign up at [pollinations.ai](https://pollinations.ai).
*   **Google Account**: To access Google Cloud Console and host the YouTube channel.

---

## 4. Google Cloud Platform (GCP) Setup

To allow the script to upload to YouTube you must configure OAuth 2.0 credentials in GCP.

1.  **Create a Project**
    Go to [Google Cloud Console](https://console.cloud.google.com/) → **New Project** → name it (e.g., `AI-Automation-Bot`) → **Create**.

2.  **Enable the YouTube Data API v3**
    In the left menu go to **APIs & Services** → **Library** → search for **"YouTube Data API v3"** → click **Enable**.

3.  **Configure the OAuth Consent Screen**
    Go to **APIs & Services** → **OAuth consent screen**:
    *   **User Type**: External → **Create**.
    *   Fill in **App name** and **User support email**.
    *   Under **Scopes** → **Add or Remove Scopes** → add `https://www.googleapis.com/auth/youtube.upload` → **Save and Continue**.
    *   Under **Test Users** → **Add Users** → enter your own Gmail address.
        > ⚠️ This step is **crucial**. While the app is in *Testing* mode only listed test users can authenticate.

4.  **Create OAuth 2.0 Credentials**
    Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**:
    *   **Application type**: Desktop app → **Create**.
    *   Click **Download JSON** on the newly created credential.
    *   **Rename** the downloaded file to `client_secrets.json` and place it in the project folder.

---

## 5. Local Environment Setup

### Folder Structure

Create a dedicated folder (e.g., `yt-bot/`) and place the files as shown:

```text
yt-bot/
├── main.py               # Main orchestration script
├── yt_uploader.py        # YouTube API upload module
└── client_secrets.json   # Google OAuth credentials (downloaded from GCP)
```

After the first successful run, two additional files will appear automatically:

```text
yt-bot/
├── token.pickle          # Saved OAuth token (auto-created on first login)
└── output_video.mp4      # The generated video (overwritten on each run)
```

### Install Dependencies

Open a terminal / PowerShell in the project folder and run:

```bash
pip install --upgrade \
  google-api-python-client \
  google-auth-oauthlib \
  google-auth-httplib2 \
  requests \
  imageio-ffmpeg
```

> **Why `imageio-ffmpeg`?** `main.py` uses `imageio_ffmpeg.get_ffmpeg_exe()` to locate a bundled ffmpeg binary when creating the image slideshow fallback. This package downloads a static ffmpeg build automatically — no separate ffmpeg installation is needed.

---

## 6. Running the Program

### Step-by-step

1.  Open a terminal / PowerShell and `cd` into the project folder.

2.  Run the script:
    ```bash
    python main.py
    ```

3.  **Enter your Pollinations Secret Key** when prompted:
    ```
    Enter your Pollinations Secret Key (sk_...): sk_xxxxxxxxxxxxxxxx
    ```

4.  **Enter a topic** for the video:
    ```
    Enter the topic for your post/video (e.g., 'Benefits of regular exercise'): Benefits of regular exercise
    ```

5.  **First-time Google authentication** — a browser window will open automatically:
    *   Sign in with the Google account you added as a test user.
    *   Click **"Advanced"** → **"Go to [Project Name] (unsafe)"** (expected for unverified apps).
    *   Tick the checkbox to grant **YouTube upload permission** → **Continue**.
    *   The browser tab will show `"The authentication flow has completed."` — you can close it.
    *   A `token.pickle` file is created in the project folder. **Subsequent runs will skip the browser step.**

6.  The script will print its progress:
    ```
    Generating text content via gemini-search...
    Text generated successfully.
    Attempting to generate video using model: grok-video (try 1)
    Video generated successfully using grok-video.
    Uploading file: output_video.mp4
    Upload successful. Video ID: xxxxxxxxxxx
    Video URL: https://www.youtube.com/watch?v=xxxxxxxxxxx
    ```

### What happens if video generation fails?

If all video model attempts return a `402` or other error, the script automatically:
1.  Downloads `FALLBACK_IMAGES` (default: 4) still images from Pollinations.
2.  Stitches them into a slideshow MP4 using the bundled ffmpeg.
3.  Uploads that slideshow to YouTube instead.

---

## 7. Customization

### `main.py` — Adjustable constants at the top of the file

```python
VIDEO_MODELS      = ("grok-video", "veo")   # Change order or add/remove models
EXACT_MATCH_PROMPT = False                  # Set True to use raw caption as video prompt
FALLBACK_IMAGE_MODEL = "flux"               # Image model for slideshow fallback
FALLBACK_IMAGES   = 4                       # Number of images in slideshow fallback
PER_IMAGE_SEC     = 3                       # Seconds per image in slideshow
OUT_VIDEO         = "output_video.mp4"      # Output filename
```

**Text prompt** — inside `run_automation()`, find the `"content"` key under `text_payload` and edit the instruction string to change the style or language of the generated caption.

### `yt_uploader.py` — Upload metadata

Inside `upload_to_youtube()`, edit the `body` dictionary:

```python
body = {
    'snippet': {
        'tags': ['AI', 'Health', 'Automation'],  # ← SEO keywords
        'categoryId': '22',                       # ← 22=People&Blogs, 27=Education, 28=Science&Tech
    },
    'status': {
        'privacyStatus': 'public',  # ← 'private' or 'unlisted' to review before publishing
    }
}
```

---

## 8. Limitations & Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `402 Payment Required` from Pollinations | Quota exceeded or plan limit | Check balance at `https://gen.pollinations.ai/account/balance`; the script retries automatically with a simplified prompt |
| Script times out during video generation | High-quality video generation is slow | Increase the `timeout` value in `requests.get(…, timeout=120)` inside `try_generate_video` |
| YouTube upload quota exceeded | Free tier: 10,000 units/day; one upload = 1,600 units ≈ **6 uploads/day** | Wait for the quota to reset (midnight Pacific Time) or request a quota increase in GCP |
| `FileNotFoundError: client_secrets.json` | Credentials file missing or misnamed | Download and rename the OAuth JSON from GCP Credentials page |
| Browser auth loop / `Access blocked` | Your Google account is not in the Test Users list | Add your Gmail in GCP → APIs & Services → OAuth consent screen → Test users |
| `token.pickle` causes auth errors | Saved token is stale or corrupted | Delete `token.pickle` and re-run to re-authenticate |
| `imageio_ffmpeg` not found | Package not installed | Run `pip install imageio-ffmpeg` |

---

**Copyright © 2026 Hugo Wong. All rights reserved**
