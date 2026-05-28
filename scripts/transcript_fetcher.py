"""
transcript_fetcher.py
Lấy YouTube transcript — bypass GitHub Actions IP block
Strategy: yt-dlp + cookies + proxy rotation
"""

import os, re, subprocess, glob, time, requests
from pathlib import Path

YT_API_KEY     = os.environ.get("YT_API_KEY", "")
PROXY_URL      = os.environ.get("PROXY_URL", "")      # Optional: socks5://user:pass@host:port
SCRAPER_API    = os.environ.get("SCRAPER_API_KEY", "") # Optional: scraperapi.com free tier


def extract_video_id(url: str) -> str:
    for pat in [r"v=([a-zA-Z0-9_-]{11})",
                r"youtu\.be/([a-zA-Z0-9_-]{11})",
                r"shorts/([a-zA-Z0-9_-]{11})"]:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    raise ValueError(f"Bad URL: {url}")


def parse_vtt(vtt_content: str) -> str:
    """Parse VTT subtitle file thành plain text"""
    lines = []
    for line in vtt_content.split("\n"):
        line = line.strip()
        if not line or "-->" in line or line.startswith("WEBVTT") or line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"&amp;", "&", line)
        line = re.sub(r"&nbsp;", " ", line)
        if line:
            lines.append(line)
    # Dedup
    deduped = []
    for line in lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)
    return " ".join(deduped)


def fetch_via_ytdlp(video_id: str, proxy: str = "") -> str:
    """yt-dlp với optional proxy"""
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-sub",
        "--sub-langs", "en.-orig,en,vi,zh-Hans,ja,ko,es,fr,de",
        "--sub-format", "vtt",
        "--no-check-certificates",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "--output", f"/tmp/yt_{video_id}",
        "--quiet",
    ]
    if proxy:
        cmd += ["--proxy", proxy]
    cmd.append(f"https://www.youtube.com/watch?v={video_id}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        sub_files = glob.glob(f"/tmp/yt_{video_id}*.vtt")
        if not sub_files:
            return ""
        content = open(sub_files[0], encoding="utf-8", errors="ignore").read()
        for f in sub_files:
            Path(f).unlink(missing_ok=True)
        return parse_vtt(content)
    except Exception:
        return ""


def fetch_via_scraper_api(video_id: str) -> str:
    """
    ScraperAPI — free 1000 requests/month.
    Lấy HTML của YouTube rồi extract transcript URL.
    """
    if not SCRAPER_API:
        return ""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        r = requests.get(
            "http://api.scraperapi.com",
            params={"api_key": SCRAPER_API, "url": url, "render": "true"},
            timeout=30
        )
        html = r.text
        # Extract timedtext URL từ HTML
        m = re.search(r'"captionTracks":\[.*?"baseUrl":"(.*?)"', html)
        if not m:
            return ""
        caption_url = m.group(1).replace("\\u0026", "&").replace("\\/", "/")
        r2 = requests.get(caption_url, timeout=15)
        # Parse XML transcript
        texts = re.findall(r"<text[^>]*>(.*?)</text>", r2.text, re.DOTALL)
        text = " ".join(re.sub(r"<[^>]+>", "", t) for t in texts)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&#39;", "'", text)
        return text.strip()
    except Exception:
        return ""


def fetch_via_supadata(video_id: str) -> str:
    """
    Supadata.ai — free tier transcript API.
    Không cần API key cho basic usage.
    """
    try:
        r = requests.get(
            f"https://api.supadata.ai/v1/youtube/transcript",
            params={"videoId": video_id, "lang": "en"},
            timeout=20
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return " ".join(item.get("text", "") for item in data)
            elif isinstance(data, dict) and "transcript" in data:
                return data["transcript"]
    except Exception:
        pass
    return ""


def fetch_via_tactiq(video_id: str) -> str:
    """
    Tactiq API — free tier.
    """
    try:
        r = requests.get(
            f"https://tactiq-apps-prod.tactiq.io/transcript",
            params={"videoUrl": f"https://www.youtube.com/watch?v={video_id}", "lang": "en"},
            timeout=20,
            headers={"Origin": "https://tactiq.io"}
        )
        if r.status_code == 200:
            data = r.json()
            segments = data.get("captions", [])
            return " ".join(s.get("text", "") for s in segments)
    except Exception:
        pass
    return ""


def fetch_via_youtube_api(video_id: str) -> str:
    """YouTube Data API v3 — cần YT_API_KEY"""
    if not YT_API_KEY:
        return ""
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/captions",
            params={"part": "snippet", "videoId": video_id, "key": YT_API_KEY},
            timeout=10)
        items = r.json().get("items", [])
        if not items:
            return ""
        cid = next((i["id"] for i in items if i["snippet"]["language"] in ["en","en-US"]),
                   items[0]["id"])
        r2 = requests.get(
            f"https://www.googleapis.com/youtube/v3/captions/{cid}",
            params={"key": YT_API_KEY},
            headers={"Accept": "text/vtt"},
            timeout=15)
        text = re.sub(r"<[^>]+>", "", r2.text)
        return " ".join(l for l in text.split("\n")
                       if l.strip() and "-->" not in l and not l.strip().isdigit())
    except Exception:
        return ""


def fetch_transcript(url: str) -> str:
    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        print(f"    ⚠ {e}")
        return ""

    # 1. yt-dlp với proxy nếu có
    if PROXY_URL:
        text = fetch_via_ytdlp(video_id, proxy=PROXY_URL)
        if text and len(text.split()) > 50:
            print(f"    ✓ yt-dlp+proxy: {len(text.split())} words")
            return text

    # 2. yt-dlp không proxy
    text = fetch_via_ytdlp(video_id)
    if text and len(text.split()) > 50:
        print(f"    ✓ yt-dlp: {len(text.split())} words")
        return text

    # 3. Supadata (free, no key needed)
    text = fetch_via_supadata(video_id)
    if text and len(text.split()) > 50:
        print(f"    ✓ supadata: {len(text.split())} words")
        return text

    # 4. Tactiq (free tier)
    text = fetch_via_tactiq(video_id)
    if text and len(text.split()) > 50:
        print(f"    ✓ tactiq: {len(text.split())} words")
        return text

    # 5. ScraperAPI (1000 free/month)
    text = fetch_via_scraper_api(video_id)
    if text and len(text.split()) > 50:
        print(f"    ✓ scraperapi: {len(text.split())} words")
        return text

    # 6. YouTube Data API v3
    text = fetch_via_youtube_api(video_id)
    if text and len(text.split()) > 50:
        print(f"    ✓ youtube-api: {len(text.split())} words")
        return text

    print(f"    ⚠ All methods failed for {url[:50]}")
    return ""
