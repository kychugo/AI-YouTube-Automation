
# 🤖 AI YouTube Automation Platform - Setup Guide

This platform uses **Pollinations.ai** (via `gemini-search`, `imagen-4`, and `seedance`) to generate content and the **YouTube Data API v3** to automatically upload videos.

## 1. Prerequisites
*   **Python 3.10+** installed on your system.
*   **Pollinations.ai Secret Key**: An API key starting with `sk_`.
*   **Google Account**: To access Google Cloud Console and host the YouTube channel.

## 2. Google Cloud Platform (GCP) Setup
To allow the script to talk to YouTube, you must configure a project in the Google Cloud Console.

1.  **Create a Project**: Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project (e.g., `AI-Automation-Bot`).
2.  **Enable API**: Search for **"YouTube Data API v3"** and click **Enable**.
3.  **OAuth Consent Screen**:
    *   Choose **User Type: External**.
    *   Fill in the App Name and Developer Email.
    *   **Scopes**: Add `https://www.googleapis.com/auth/youtube.upload`.
    *   **Test Users**: Add your own Gmail address (Crucial! Only test users can log in while the app is in "Testing" status).
4.  **Create Credentials**:
    *   Go to **Credentials** -> **Create Credentials** -> **OAuth client ID**.
    *   Select **Application type: Desktop App**.
    *   Download the **JSON file**.
    *   **Rename** the downloaded file to `client_secrets.json`.

## 3. Local Environment Setup
Create a dedicated folder for your bot (e.g., `C:\imp\yt-bot`) and organize your files.

### Folder Structure
```text
yt-bot/
├── main.py             # The main execution script
├── yt_uploader.py      # The YouTube API logic
└── client_secrets.json # The Google credentials file
```

### Install Dependencies
Run the following command in your terminal/PowerShell:
```powershell
pip install --upgrade google-api-python-client google-auth-oauthlib google-auth-httplib2 requests
```

## 4. First-Time Run & Authentication
1.  Run the script: `python main.py`.
2.  Enter your **Pollinations Secret Key** when prompted.
3.  **Browser Auth**: A browser window will pop up asking you to log in to your Google Account.
    *   Since the app is not verified by Google, click **"Advanced"** -> **"Go to [Project Name] (unsafe)"**.
    *   Check the box to grant **Upload permissions**.
4.  **Token Generation**: After a successful login, a file named `token.pickle` will be created in your folder. 
    *   *Note:* You won't need to log in through the browser again as long as this file exists.

## 5. What Needs to be Modified (Customization)

### In `main.py`:
*   **Topic**: Change the `topic` variable to generate content about different subjects.
*   **Prompts**: Modify the `content` strings in the text/video generation sections to change the "vibe" or style of the AI output.
*   **Video Models**: If `seedance` is slow or failing, you can reorder the `video_models` list (e.g., put `veo` first).

### In `yt_uploader.py`:
*   **Privacy Status**: Inside the `upload_to_youtube` function, change `'privacyStatus': 'public'` to `'private'` if you want to review videos before they go live.
*   **Category ID**: The default is `'22'` (People & Blogs). You can change this to `'27'` (Education) or `'28'` (Science & Tech).
*   **Tags**: Modify the list in `tags` to improve your video's SEO.

## 6. Limitations & Troubleshooting
*   **YouTube Quota**: The free tier provides **10,000 units** per day. One upload costs **1,600 units**. You can upload roughly **6 videos per day**.
*   **Pollinations Balance**: Check your balance at `https://gen.pollinations.ai/account/balance` if generation fails.
*   **Timeout**: Generating high-quality AI video takes time. If the script crashes, ensure the `timeout` in the `requests.get` call is at least `120` seconds.
---
**Copyright © 2026 Hugo Wong. All rights reserved**
