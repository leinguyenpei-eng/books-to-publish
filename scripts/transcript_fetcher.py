"""
transcript_fetcher.py
Lấy YouTube transcript với 3 phương pháp fallback:
1. youtube-transcript-api trực tiếp (hoạt động local)
2. YouTube Data API v3 (captions endpoint - cần API key)  
3. yt-dlp (bypass block tốt nhất cho GitHub Actions)
"""

import os, re, subprocess, json, requests, time
from pathlib import Path

YT_API_KEY = os.environ.get("YT_API_KEY", "")


def extract_video_id(url: str) -> str:
    for pat in [r"v=([a-zA-Z0-9_-]{11})",
                r"youtu\.be/([a-zA-Z0-9_-]{11})",
                r"shorts/([a-zA-Z0-9_-]{11})"]:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    raise ValueError(f"Bad URL: {url}")


def fetch_via_ytdlp(video_id: str) -> str:
    """
    yt-dlp tốt nhất cho GitHub Actions — bypass YouTube block.
    Tự động lấy auto-generated subtitles mọi ngôn ngữ.
    """
    try:
        # Download subtitle file (không download video)
        result = subprocess.run([
            "yt-dlp",
            "--skip-download",
            "--write-auto-sub",
            "--sub-langs", "en,vi,zh,ja,ko,es,fr,de,pt,ru",
            "--sub-format", "vtt",
            "--output", f"/tmp/yt_{video_id}",
            f"https://www.youtube.com/watch?v={video_id}"
        ], capture_output=True, text=True, timeout=60)

        # Tìm file subtitle vừa tải
        import glob
        sub_files = glob.glob(f"/tmp/yt_{video_id}*.vtt")
        if not sub_files:
            return ""

        # Parse VTT file
        vtt_content = open(sub_files[0], encoding="utf-8", errors="ignore").read()
        # Xóa file tạm
        for f in sub_files:
            Path(f).unlink(missing_ok=True)

        # Lấy text từ VTT
        lines = []
        for line in vtt_content.split("\n"):
            line = line.strip()
            # Skip timestamps, headers, empty lines
            if not line or "-->" in line or line.startswith("WEBVTT") or line.isdigit():
                continue
            # Xóa HTML tags
            line = re.sub(r"<[^>]+>", "", line)
            if line:
                lines.append(line)

        # Dedup consecutive duplicates (VTT có nhiều dòng trùng)
        deduped = []
        for line in lines:
            if not deduped or line != deduped[-1]:
                deduped.append(line)

        return " ".join(deduped)

    except Exception as e:
        return ""


def fetch_via_transcript_api(video_id: str) -> str:
    """youtube-transcript-api v1.2.x API mới"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        
        # Thử list trước để biết ngôn ngữ nào available
        try:
            tlist = api.list(video_id)
            langs = ['en','vi','zh','ja','ko','es','fr','de','pt','ru']
            
            # Thử manual transcript trước
            transcript = None
            for t in tlist:
                if t.language_code in langs and not t.is_generated:
                    transcript = t
                    break
            # Fallback auto-generated
            if not transcript:
                for t in tlist:
                    if t.language_code in langs:
                        transcript = t
                        break
            if not transcript:
                transcript = next(iter(tlist))
            
            fetched = transcript.fetch()
            return " ".join(s.text for s in fetched)
        except Exception:
            # Thử fetch trực tiếp
            result = api.fetch(video_id, languages=['en','vi','zh','ja','ko'])
            return " ".join(s.text for s in result)

    except Exception as e:
        return ""


def fetch_via_youtube_api(video_id: str) -> str:
    """
    YouTube Data API v3 — lấy caption track.
    Cần YT_API_KEY trong GitHub Secrets.
    """
    if not YT_API_KEY:
        return ""
    try:
        # Get caption list
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/captions",
            params={"part": "snippet", "videoId": video_id, "key": YT_API_KEY},
            timeout=10)
        captions = r.json().get("items", [])
        if not captions:
            return ""

        # Prefer English, then any language
        caption_id = None
        for cap in captions:
            if cap["snippet"]["language"] in ["en", "en-US"]:
                caption_id = cap["id"]
                break
        if not caption_id:
            caption_id = captions[0]["id"]

        # Download caption content
        r2 = requests.get(
            f"https://www.googleapis.com/youtube/v3/captions/{caption_id}",
            params={"key": YT_API_KEY},
            headers={"Accept": "text/vtt"},
            timeout=15)
        
        # Parse text
        text = re.sub(r"<[^>]+>", "", r2.text)
        text = "\n".join(l for l in text.split("\n") 
                        if l.strip() and "-->" not in l and not l.strip().isdigit())
        return text

    except Exception:
        return ""


def fetch_transcript(url: str) -> str:
    """
    Main function — thử 3 phương pháp theo thứ tự.
    GitHub Actions: yt-dlp tốt nhất vì bypass YouTube block.
    """
    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        print(f"    ⚠ {e}")
        return ""

    # Method 1: yt-dlp (tốt nhất cho GitHub Actions)
    text = fetch_via_ytdlp(video_id)
    if text and len(text.split()) > 100:
        print(f"    ✓ yt-dlp: {len(text.split())} words")
        return text

    # Method 2: youtube-transcript-api
    text = fetch_via_transcript_api(video_id)
    if text and len(text.split()) > 100:
        print(f"    ✓ transcript-api: {len(text.split())} words")
        return text

    # Method 3: YouTube Data API v3
    text = fetch_via_youtube_api(video_id)
    if text and len(text.split()) > 50:
        print(f"    ✓ YouTube API: {len(text.split())} words")
        return text

    print(f"    ⚠ All methods failed for {url[:50]}")
    return ""
