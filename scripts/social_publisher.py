"""
social_publisher.py
Facebook posts: 5 types × EN + VI = 10 posts total.
Auto-post via Meta Graph API if FB_PAGE_TOKEN set,
otherwise save to file for manual copy-paste.
"""

import os, requests, time
from pathlib import Path
from datetime import datetime

CLAUDE_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "")
FB_TOKEN    = os.environ.get("FB_PAGE_TOKEN", "")
FB_PAGE_ID  = os.environ.get("FB_PAGE_ID", "")
OUTPUT_DIR  = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

POST_TYPES = {
    "launch": {
        "en": "Write a LAUNCH announcement post. Excited tone, announce the book is now live, include price and buy links. Make it feel like a celebration.",
        "vi": "Viết post LAUNCH sách mới. Giọng hào hứng, thông báo sách đã ra mắt, kèm giá và link mua. Tạo cảm giác như ăn mừng.",
    },
    "tease": {
        "en": "Write a TEASER post. Share 1 surprising insight or counterintuitive tip from the book without giving everything away. Build curiosity and make people want to know more.",
        "vi": "Viết post TEASER. Chia sẻ 1 insight bất ngờ hoặc mẹo đi ngược số đông từ sách mà không tiết lộ hết. Tạo sự tò mò.",
    },
    "value": {
        "en": "Write a VALUE post. Share 3-5 actionable tips from the book for free. Genuinely helpful content. Soft CTA at end: 'Want the full guide?'",
        "vi": "Viết post GIÁ TRỊ. Chia sẻ 3-5 tips thực tế từ sách miễn phí. Nội dung thật sự hữu ích. Kết bằng CTA nhẹ: 'Muốn có đầy đủ?'",
    },
    "story": {
        "en": "Write a STORY post. Tell a relatable story of someone struggling with this topic (could be the author's journey), then how the approach in the book helped them. Emotional, personal.",
        "vi": "Viết post KỂ CHUYỆN. Kể câu chuyện dễ relate về ai đó gặp khó khăn với chủ đề này (có thể là hành trình của tác giả), rồi cách tiếp cận trong sách đã giúp. Cảm xúc, cá nhân.",
    },
    "urgency": {
        "en": "Write an URGENCY post. Last call framing. Remind people what they're missing out on. Could mention limited time, or simply 'still available for those who haven't grabbed it yet'. Not pushy — thoughtful.",
        "vi": "Viết post URGENCY. Nhắc nhở lần cuối. Nói về những gì đang bỏ lỡ. Có thể dùng framing 'vẫn còn kịp'. Không aggressive — chân thành.",
    },
}

SCHEDULE = ["Day 1 (Launch day)", "Day 3", "Day 5 (Value bomb)", "Day 8 (Story)", "Day 14 (Last push)"]
POST_ORDER = ["launch", "tease", "value", "story", "urgency"]


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
            log(f"  ⚠ Claude: {e} — trying Gemini")
    if GEMINI_KEY:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1024}},
            timeout=30)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    raise RuntimeError("No AI keys available")


def generate_posts(config: dict, buy_links: dict) -> dict:
    title       = config.get("title", "Untitled")
    subtitle    = config.get("subtitle", "")
    niche       = config.get("niche", "Self-help")
    price_usd   = config.get("price_usd", 9.99)
    price_vnd   = config.get("price_vnd", 250000)
    description = config.get("description", "")
    links_str   = "\n".join(f"🔗 {p}: {u}" for p, u in buy_links.items() if u) or "Link coming soon"

    all_posts = {}
    for post_type, tasks in POST_TYPES.items():
        all_posts[post_type] = {}
        for lang, task in tasks.items():
            log(f"  ✍ {post_type} ({lang.upper()})...")
            lang_note = "Write in English." if lang == "en" else "Viết hoàn toàn bằng Tiếng Việt tự nhiên, thân thiện."
            price_str = f"${price_usd}" if lang == "en" else f"{price_vnd:,}đ"

            prompt = f"""{lang_note}

Book: "{title}" — {subtitle}
Genre: {niche} | Price: {price_str}
Description: {description}
Buy links:
{links_str}

Task: {task}

Facebook post rules:
- 150-250 words
- 2-3 emojis max (not overdone)
- Include book title naturally
- End with buy link
- Sound like a real human sharing value, NOT a sales ad
- Line breaks for readability

Write the post:"""

            try:
                all_posts[post_type][lang] = call_ai(prompt)
            except Exception as e:
                log(f"  ⚠ {post_type}/{lang} failed: {e}")
                all_posts[post_type][lang] = f"[Generation failed: {e}]"
            time.sleep(2)

    return all_posts


def save_posts(posts: dict, config: dict) -> Path:
    title    = config.get("title", "Untitled")
    out_path = OUTPUT_DIR / f"{title}_facebook_posts.txt"

    lines = [
        f"📚 FACEBOOK POSTS — {title}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 60,
        "Post schedule: 1 post every 2-3 days starting launch day.",
        "=" * 60, "",
    ]

    for i, post_type in enumerate(POST_ORDER):
        day = SCHEDULE[i] if i < len(SCHEDULE) else f"Post {i+1}"
        lines += [f"\n{'─'*50}", f"POST {i+1} — {day} — {post_type.upper()}", f"{'─'*50}",
                  "\n🇺🇸 ENGLISH:", posts.get(post_type, {}).get("en", "[not generated]"),
                  "\n🇻🇳 TIẾNG VIỆT:", posts.get(post_type, {}).get("vi", "[not generated]"), ""]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"✓ Facebook posts: {out_path.name}")
    return out_path


def post_to_facebook(text: str, image_path: Path = None) -> bool:
    if not FB_TOKEN or not FB_PAGE_ID:
        return False
    try:
        if image_path and image_path.exists():
            with open(image_path, "rb") as f:
                r = requests.post(f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos",
                                  data={"message": text, "access_token": FB_TOKEN},
                                  files={"source": f}, timeout=30)
        else:
            r = requests.post(f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed",
                              json={"message": text, "access_token": FB_TOKEN}, timeout=30)
        result = r.json()
        if "id" in result:
            log(f"  ✓ Posted to Facebook: {result['id']}"); return True
        log(f"  ⚠ Facebook: {result}"); return False
    except Exception as e:
        log(f"  ⚠ Facebook API: {e}"); return False


def run_social_publisher(config: dict, buy_links: dict = None, cover_path: Path = None):
    if buy_links is None:
        buy_links = {}
    title = config.get("title", "Untitled")
    log(f"\n📱 Facebook posts: {title}")

    posts = generate_posts(config, buy_links)
    posts_file = save_posts(posts, config)

    if FB_TOKEN and FB_PAGE_ID:
        launch_en = posts.get("launch", {}).get("en", "")
        if launch_en:
            log("  → Auto-posting launch post to Facebook...")
            post_to_facebook(launch_en, cover_path)
    else:
        log(f"  ℹ No FB token — posts saved to {posts_file.name}")

    return posts_file
