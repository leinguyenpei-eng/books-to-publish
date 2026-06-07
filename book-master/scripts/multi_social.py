"""
multi_social.py
TikTok script / Instagram / LinkedIn / Twitter — EN + VI
Each platform gets its own format, tone, and structure.
"""

import os, requests, time
from pathlib import Path
from datetime import datetime

CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PLATFORMS = {
    "tiktok_script": {
        "desc": "TikTok video script (60-90 sec)",
        "en": "Write a TikTok VIDEO SCRIPT (60-90 seconds). Format:\n[HOOK - 5 sec]: Scroll-stopping opening line\n[PROBLEM - 10 sec]: Relate to viewer's pain point\n[3 KEY INSIGHTS - 40 sec]: One insight per beat, very punchy\n[CTA - 10 sec]: Simple action step\nInclude: suggested on-screen text captions, transitions cues. Short punchy sentences only.",
        "vi": "Viết SCRIPT video TikTok (60-90 giây). Format:\n[HOOK - 5 giây]: Câu mở đầu khiến người ta dừng scroll\n[VẤN ĐỀ - 10 giây]: Relate với pain point của người xem\n[3 INSIGHT - 40 giây]: Mỗi insight 1 beat ngắn gọn\n[CTA - 10 giây]: Hành động đơn giản\nBao gồm: gợi ý text hiện trên màn hình, cues chuyển cảnh.",
    },
    "instagram_caption": {
        "desc": "Instagram carousel caption + hashtags",
        "en": "Write an Instagram CAROUSEL caption.\nSlide 1: Hook line (makes people swipe)\nSlides 2-7: One insight each — short, visual-friendly, 1-2 sentences max\nSlide 8: CTA + where to buy\nThen: 20 hashtags grouped (5 broad, 5 niche, 5 micro, 5 community tags)",
        "vi": "Viết caption CAROUSEL Instagram.\nSlide 1: Hook (khiến người ta vuốt tiếp)\nSlide 2-7: Mỗi slide 1 insight ngắn, 1-2 câu tối đa\nSlide 8: CTA + link mua\nThêm: 20 hashtag chia nhóm (5 broad, 5 niche, 5 micro, 5 community).",
    },
    "linkedin_post": {
        "desc": "LinkedIn long-form post",
        "en": "Write a LinkedIn POST (200-300 words).\nProfessional but warm. Start with a bold counterintuitive statement.\nUse single-sentence line breaks (LinkedIn style).\nShare 2-3 lessons from the book as professional insights.\nEnd with a question to drive comments.\nMention the book as a resource, not a hard sell.",
        "vi": "Viết LinkedIn POST (200-300 chữ).\nChuyên nghiệp nhưng thân thiện. Bắt đầu bằng câu đi ngược số đông.\nXuống hàng từng câu (LinkedIn style).\nChia sẻ 2-3 bài học từ sách như professional insights.\nKết bằng câu hỏi tạo comment.\nGiới thiệu sách như tài nguyên, không phải quảng cáo.",
    },
    "twitter_thread": {
        "desc": "Twitter/X thread (8-10 tweets)",
        "en": "Write a Twitter/X THREAD of 8-10 tweets.\nTweet 1: Hook that makes people stop scrolling — bold claim or surprising stat\nTweets 2-8: One insight per tweet, max 240 chars each, punchy\nTweet 9: Summary of key takeaways\nTweet 10: CTA with buy link\nNumber each tweet: (1/10), (2/10)...\nUse line breaks within tweets for readability.",
        "vi": "Viết Twitter/X THREAD 8-10 tweets.\nTweet 1: Hook khiến người ta dừng lại — claim mạnh hoặc stat bất ngờ\nTweet 2-8: Mỗi tweet 1 insight, tối đa 240 ký tự, ngắn gọn\nTweet 9: Tóm tắt key takeaways\nTweet 10: CTA + link mua\nĐánh số: (1/10), (2/10)...",
    },
}

SCHEDULE = {
    "tiktok_script":    "Day 1 (Launch) — highest reach for new audiences",
    "instagram_caption": "Day 2 — visual carousel, saves = algorithm boost",
    "linkedin_post":    "Day 3 — professional buyers",
    "twitter_thread":   "Day 5 — discussion + shares",
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def call_ai(prompt: str) -> str:
    if CLAUDE_KEY:
        try:
            r = requests.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CLAUDE_KEY, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": "claude-haiku-4-5", "max_tokens": 1024,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=60)
            data = r.json()
            if "content" in data:
                return data["content"][0]["text"].strip()
        except Exception as e:
            log(f"  ⚠ Claude: {e}")
    if GEMINI_KEY:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1024}},
            timeout=30)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    raise RuntimeError("No AI keys")


def generate_platform_content(config: dict, buy_links: dict) -> dict:
    title     = config.get("title", "Untitled")
    subtitle  = config.get("subtitle", "")
    niche     = config.get("niche", "Self-help")
    price_usd = config.get("price_usd", 9.99)
    desc      = config.get("description", "")
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
Description: {desc}
Buy links: {links_str}

{info[lang if lang in info else 'en']}

Write now:"""

            try:
                all_content[platform][lang] = call_ai(prompt)
            except Exception as e:
                log(f"  ⚠ {platform}/{lang}: {e}")
                all_content[platform][lang] = f"[Error: {e}]"
            time.sleep(2)

    return all_content


def save_social_content(content: dict, config: dict) -> Path:
    title    = config.get("title", "Untitled")
    out_path = OUTPUT_DIR / f"{title}_social_content.txt"

    lines = [
        f"📱 SOCIAL MEDIA CONTENT — {title}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 60,
        "\nPOSTING SCHEDULE:",
        "Day 1: TikTok (launch + reach)", "Day 2: Instagram carousel",
        "Day 3: LinkedIn", "Day 5: Twitter/X thread",
        "Day 7+: Facebook posts (see facebook_posts.txt)",
        "\n" + "=" * 60,
    ]

    for platform, info in PLATFORMS.items():
        sched = SCHEDULE.get(platform, platform)
        lines += [f"\n{'─'*50}", f"📍 {sched.upper()}", f"   [{info['desc']}]", f"{'─'*50}",
                  "\n🇺🇸 ENGLISH:", content.get(platform, {}).get("en", "[not generated]"),
                  "\n🇻🇳 TIẾNG VIỆT:", content.get(platform, {}).get("vi", "[not generated]"), ""]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"✓ Social content: {out_path.name}")
    return out_path


def run_multi_social(config: dict, buy_links: dict = None, cover_path: Path = None):
    if buy_links is None:
        buy_links = {}
    title = config.get("title", "Untitled")
    log(f"\n📱 Multi-platform content: {title}")
    content = generate_platform_content(config, buy_links)
    return save_social_content(content, config)
