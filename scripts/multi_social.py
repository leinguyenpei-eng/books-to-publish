"""
multi_social.py
Tạo content cho TikTok, Instagram, LinkedIn, Twitter/X
mỗi platform có format + tone riêng
"""

import os, requests, time, json
from pathlib import Path
from datetime import datetime

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PLATFORMS = {
    "tiktok_script": {
        "desc": "TikTok video script (60-90 sec, hook-heavy)",
        "en": "Write a TikTok video SCRIPT (60-90 seconds). Format: [HOOK - 5 sec], [PROBLEM - 10 sec], [3 KEY INSIGHTS - 40 sec], [CTA - 10 sec]. Very punchy, short sentences, pattern interrupts. Include suggested on-screen text captions.",
        "vi": "Viết SCRIPT video TikTok (60-90 giây). Format: [HOOK - 5 giây], [VẤN ĐỀ - 10 giây], [3 INSIGHT CHÍNH - 40 giây], [CTA - 10 giây]. Câu ngắn, mạnh, có pattern interrupt. Ghi rõ text hiện trên màn hình.",
    },
    "instagram_caption": {
        "desc": "Instagram carousel caption + hashtags",
        "en": "Write an Instagram carousel caption. Slide 1: hook line. Slides 2-7: one insight each (short, visual-friendly). Slide 8: CTA. Then add 20 relevant hashtags grouped by size (broad, niche, micro).",
        "vi": "Viết caption cho Instagram carousel. Slide 1: câu hook. Slide 2-7: mỗi slide 1 insight ngắn, visual-friendly. Slide 8: CTA. Thêm 20 hashtag liên quan (broad, niche, micro).",
    },
    "linkedin_post": {
        "desc": "LinkedIn long-form post for professionals",
        "en": "Write a LinkedIn post (200-300 words). Professional but warm tone. Start with a bold statement or counterintuitive insight. Use single-sentence line breaks for readability. End with a question to drive comments. Include the book as a resource, not a hard sell.",
        "vi": "Viết LinkedIn post (200-300 chữ). Giọng chuyên nghiệp nhưng thân thiện. Bắt đầu bằng câu mạnh hoặc insight đi ngược số đông. Xuống hàng từng câu. Kết bằng câu hỏi tạo comment. Giới thiệu sách như tài nguyên, không phải quảng cáo cứng.",
    },
    "twitter_thread": {
        "desc": "Twitter/X thread (8-10 tweets)",
        "en": "Write a Twitter/X thread of 8-10 tweets. Tweet 1: hook that makes people stop scrolling. Tweets 2-8: one insight per tweet, max 240 chars each. Tweet 9: summary. Tweet 10: CTA with link. Number each tweet (1/10, 2/10...).",
        "vi": "Viết Twitter/X thread 8-10 tweets. Tweet 1: hook khiến người ta phải dừng scroll. Tweet 2-8: mỗi tweet 1 insight, tối đa 240 ký tự. Tweet 9: tổng kết. Tweet 10: CTA + link. Đánh số từng tweet (1/10, 2/10...).",
    },
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def call_ai(prompt: str) -> str:
    """Claude API trực tiếp, fallback Gemini"""
    claude_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if claude_key:
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": claude_key,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001",
                      "max_tokens": 1024,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=60)
            data = r.json()
            if "content" in data:
                return data["content"][0]["text"].strip()
        except Exception as e:
            log(f"  ⚠ Claude failed: {e}, trying Gemini...")
    # Fallback Gemini
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1024}},
        timeout=30)
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def generate_platform_content(config: dict, buy_links: dict) -> dict:
    title       = config.get("title", "Untitled")
    subtitle    = config.get("subtitle", "")
    niche       = config.get("niche", "Self-help")
    price_usd   = config.get("price_usd", 9.99)
    description = config.get("description", "")

    links_str = " | ".join(f"{p}: {u}" for p, u in buy_links.items() if u) or "Link TBD"

    all_content = {}

    for platform, info in PLATFORMS.items():
        all_content[platform] = {}
        for lang in ["en", "vi"]:
            log(f"  ✍ {platform} ({lang.upper()})...")
            lang_note = "Write in English." if lang == "en" else "Viết bằng Tiếng Việt tự nhiên."
            price_str = f"${price_usd}" if lang == "en" else f"{int(config.get('price_vnd', 250000)):,}đ"

            prompt = f"""{lang_note}

Book: "{title}" — {subtitle}
Genre: {niche} | Price: {price_str}
Description: {description}
Buy links: {links_str}

{info[lang]}

Write now:"""

            try:
                content = call_ai(prompt)
                all_content[platform][lang] = content
            except Exception as e:
                log(f"  ⚠ Failed {platform}/{lang}: {e}")
                all_content[platform][lang] = f"[Error: {e}]"

            time.sleep(2)

    return all_content


def save_social_content(content: dict, config: dict) -> Path:
    title    = config.get("title", "Untitled")
    out_path = OUTPUT_DIR / f"{title}_social_content.txt"

    schedule = {
        "tiktok_script":    "Day 1 (Launch) — Post TikTok video",
        "instagram_caption": "Day 2 — Instagram carousel",
        "linkedin_post":    "Day 3 — LinkedIn post",
        "twitter_thread":   "Day 5 — Twitter/X thread",
    }

    lines = [
        f"📱 SOCIAL MEDIA CONTENT — {title}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 60,
        "",
        "POSTING SCHEDULE:",
        "Day 1: TikTok (highest reach for new audiences)",
        "Day 2: Instagram carousel (visual, saves = algorithm boost)",
        "Day 3: LinkedIn (professional buyers)",
        "Day 5: Twitter/X thread (discussion, shares)",
        "Day 7: Facebook (from social_publisher.py — launch post)",
        "Day 10: Facebook (value post)",
        "Day 14: All platforms (urgency posts)",
        "",
        "=" * 60,
    ]

    for platform, info in PLATFORMS.items():
        sched = schedule.get(platform, platform)
        lines.append(f"\n{'─'*50}")
        lines.append(f"📍 {sched.upper()}")
        lines.append(f"   [{info['desc']}]")
        lines.append(f"{'─'*50}")

        lines.append("\n🇺🇸 ENGLISH:")
        lines.append(content.get(platform, {}).get("en", "[not generated]"))

        lines.append("\n🇻🇳 TIẾNG VIỆT:")
        lines.append(content.get(platform, {}).get("vi", "[not generated]"))
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"✓ Social content saved: {out_path}")
    return out_path


def run_multi_social(config: dict, buy_links: dict = None, cover_path: Path = None):
    if buy_links is None:
        buy_links = {}
    title = config.get("title", "Untitled")
    log(f"\n📱 Generating multi-platform content for: {title}")

    content  = generate_platform_content(config, buy_links)
    out_file = save_social_content(content, config)
    log(f"  ✓ All platforms done: {out_file}")
    return out_file
