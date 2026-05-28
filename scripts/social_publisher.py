"""
social_publisher.py
Tự động tạo Facebook posts quảng bá sách khi pipeline hoàn thành.
- 5 post variations (launch, tease, value, testimonial-style, urgency)
- EN + VI versions
- Lưu file .txt để copy paste, hoặc dùng Meta Graph API nếu có token
"""

import os, requests, time, json
from pathlib import Path
from datetime import datetime

GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "")
FB_TOKEN     = os.environ.get("FB_PAGE_TOKEN", "")   # Optional: Meta Graph API
FB_PAGE_ID   = os.environ.get("FB_PAGE_ID", "")      # Optional
CLAUDE_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
OUTPUT_DIR   = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 5 post types × EN + VI
POST_TYPES = {
    "launch": {
        "en": "Write a LAUNCH announcement post. Excited tone, announce the book is live, include price and all buy links.",
        "vi": "Viết post LAUNCH sách mới. Giọng hào hứng, thông báo sách đã ra mắt, kèm giá và link mua.",
    },
    "tease": {
        "en": "Write a TEASER post. Share 1 surprising insight or tip from the book without giving everything away. Build curiosity.",
        "vi": "Viết post TEASER. Chia sẻ 1 insight thú vị từ sách mà không tiết lộ hết. Tạo sự tò mò.",
    },
    "value": {
        "en": "Write a VALUE post. Share 3-5 actionable tips from the book for free. End with soft CTA to buy for the full guide.",
        "vi": "Viết post GIÁ TRỊ. Chia sẻ 3-5 tips thực tế từ sách miễn phí. Kết bằng CTA mềm để mua sách đầy đủ.",
    },
    "story": {
        "en": "Write a STORY/TESTIMONIAL-style post. Tell a relatable story of someone struggling with this topic, then how the book's approach helped.",
        "vi": "Viết post KỂ CHUYỆN. Kể câu chuyện dễ relate về ai đó gặp khó khăn với chủ đề này, rồi cách sách giúp giải quyết.",
    },
    "urgency": {
        "en": "Write an URGENCY post. Last call, limited-time framing (or just 'still available'), remind people what they're missing out on.",
        "vi": "Viết post URGENCY. Nhắc nhở lần cuối, tạo cảm giác khan hiếm hoặc 'vẫn còn kịp', nhắc lại giá trị đang bỏ lỡ.",
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


def generate_posts(config: dict, buy_links: dict) -> dict:
    """Tạo 5 loại post × 2 ngôn ngữ = 10 posts tổng"""
    title       = config.get("title", "Untitled")
    subtitle    = config.get("subtitle", "")
    niche       = config.get("niche", "Self-help")
    price_usd   = config.get("price_usd", 9.99)
    price_vnd   = config.get("price_vnd", 250000)
    description = config.get("description", "")

    # Build links string
    links_str = ""
    for platform, url in buy_links.items():
        if url:
            links_str += f"\n🔗 {platform}: {url}"

    all_posts = {}

    for post_type, tasks in POST_TYPES.items():
        all_posts[post_type] = {}
        for lang, task in tasks.items():
            log(f"  ✍ {post_type} post ({lang.upper()})...")

            lang_note = "Write in English." if lang == "en" else "Viết hoàn toàn bằng Tiếng Việt tự nhiên, thân thiện."
            price_str = f"${price_usd}" if lang == "en" else f"{price_vnd:,}đ"

            prompt = f"""{lang_note}

Book details:
- Title: "{title}"
- Subtitle: "{subtitle}"
- Genre: {niche}
- Price: {price_str}
- Description: {description}
- Buy links:{links_str}

Task: {task}

Facebook post requirements:
- 150-250 words
- Use 2-3 relevant emojis (not overdone)
- Include the book title naturally
- End with the buy link(s)
- Sound like a real person sharing something valuable, NOT a sales ad
- Use line breaks for readability

Write the post now:"""

            try:
                post = call_ai(prompt)
                all_posts[post_type][lang] = post
            except Exception as e:
                log(f"  ⚠ Failed {post_type}/{lang}: {e}")
                all_posts[post_type][lang] = f"[Generation failed: {e}]"

            time.sleep(2)

    return all_posts


def save_posts(posts: dict, config: dict) -> Path:
    """Lưu tất cả posts ra file .txt dễ copy-paste"""
    title    = config.get("title", "Untitled")
    out_path = OUTPUT_DIR / f"{title}_facebook_posts.txt"

    lines = [
        f"📚 FACEBOOK POSTS — {title}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 60,
        "Copy-paste these posts to Facebook.",
        "Post schedule suggestion: 1 post every 2-3 days after launch.",
        "=" * 60,
        "",
    ]

    schedule = ["Day 1 (Launch day)", "Day 3", "Day 5", "Day 8", "Day 14 (Last push)"]
    post_order = ["launch", "tease", "value", "story", "urgency"]

    for i, post_type in enumerate(post_order):
        day = schedule[i] if i < len(schedule) else f"Post {i+1}"
        lines.append(f"\n{'─'*50}")
        lines.append(f"POST {i+1} — {day} — {post_type.upper()}")
        lines.append(f"{'─'*50}")

        # English version
        lines.append("\n🇺🇸 ENGLISH VERSION:")
        lines.append(posts.get(post_type, {}).get("en", "[not generated]"))

        # Vietnamese version
        lines.append("\n🇻🇳 TIẾNG VIỆT:")
        lines.append(posts.get(post_type, {}).get("vi", "[not generated]"))
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"✓ Facebook posts saved: {out_path}")
    return out_path


def post_to_facebook(post_text: str, image_path: Path = None) -> bool:
    """
    Đăng thẳng lên Facebook Page (cần FB_PAGE_TOKEN + FB_PAGE_ID).
    Nếu không có token → chỉ lưu file để copy-paste thủ công.
    """
    if not FB_TOKEN or not FB_PAGE_ID:
        return False

    try:
        if image_path and image_path.exists():
            # Post with image
            with open(image_path, "rb") as f:
                r = requests.post(
                    f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos",
                    data={"message": post_text, "access_token": FB_TOKEN},
                    files={"source": f},
                    timeout=30
                )
        else:
            # Text only post
            r = requests.post(
                f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed",
                json={"message": post_text, "access_token": FB_TOKEN},
                timeout=30
            )
        result = r.json()
        if "id" in result:
            log(f"  ✓ Posted to Facebook: {result['id']}")
            return True
        else:
            log(f"  ⚠ Facebook post failed: {result}")
            return False
    except Exception as e:
        log(f"  ⚠ Facebook API error: {e}")
        return False


def run_social_publisher(config: dict, buy_links: dict = None, cover_path: Path = None):
    """Entry point — gọi từ build_book.py sau khi sách xong"""
    if buy_links is None:
        buy_links = {}

    title = config.get("title", "Untitled")
    log(f"\n📱 Generating Facebook posts for: {title}")

    # Generate all posts
    posts = generate_posts(config, buy_links)

    # Save to file (luôn làm)
    posts_file = save_posts(posts, config)

    # Auto-post launch post nếu có FB token + cover image
    if FB_TOKEN and FB_PAGE_ID:
        launch_post = posts.get("launch", {}).get("en", "")
        if launch_post:
            log("  → Auto-posting launch post to Facebook Page...")
            post_to_facebook(launch_post, cover_path)
    else:
        log("  ℹ No FB_PAGE_TOKEN — posts saved to file for manual posting")
        log(f"  📄 File: {posts_file}")

    return posts_file
