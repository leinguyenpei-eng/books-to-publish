"""
cover_generator.py
Tự động tạo bìa sách đẹp:
1. Gemini tạo prompt mô tả hình ảnh phù hợp với niche
2. Imagen (Gemini) generate ảnh nền
3. Pillow overlay title + author lên ảnh → bìa hoàn chỉnh
"""

import os, requests, base64, textwrap
from pathlib import Path
from datetime import datetime
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    PIL_OK = True
except ImportError:
    PIL_OK = False

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# KDP ebook cover: 2560×1600 px (1.6:1 ratio) — Amazon recommended
COVER_W, COVER_H = 1600, 2560

NICHE_STYLE = {
    "Self-help":    "warm golden sunrise light, clean minimal, soft bokeh, inspirational, professional book cover background",
    "Business":     "dark navy blue, geometric patterns, corporate minimal, sharp lines, premium texture",
    "Finance":      "deep green with gold accents, subtle dollar/growth motifs, luxury minimal",
    "Health":       "fresh green nature, clean white space, calm wellness spa atmosphere",
    "How-to":       "bright clean workspace, tools or hands working, clear focused composition",
    "default":      "abstract professional gradient, clean minimal, book cover background",
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def generate_cover_prompt(title: str, niche: str) -> str:
    """Dùng Gemini text để tạo prompt hình ảnh tốt hơn"""
    style = NICHE_STYLE.get(niche, NICHE_STYLE["default"])
    prompt = f"""Create a detailed image generation prompt for a professional book cover background.
Book title: "{title}"
Genre/niche: {niche}
Style reference: {style}

Requirements:
- NO text in the image
- Full bleed background only (no borders)
- Cinematic lighting
- Premium, publishable quality
- Suitable as background for white text overlay

Return ONLY the image prompt, max 100 words, no explanation."""

    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.9, "maxOutputTokens": 150}},
        timeout=30
    )
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def generate_image_gemini(prompt: str) -> Image.Image | None:
    """Gọi Gemini Imagen để tạo ảnh nền"""
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={GEMINI_KEY}",
            json={
                "instances": [{"prompt": prompt}],
                "parameters": {"sampleCount": 1, "aspectRatio": "9:16"}
            },
            timeout=60
        )
        data = r.json()
        if "predictions" in data:
            img_b64 = data["predictions"][0]["bytesBase64Encoded"]
            return Image.open(BytesIO(base64.b64decode(img_b64)))
    except Exception as e:
        log(f"  ⚠ Imagen error: {e}")
    return None


def create_gradient_background(niche: str) -> Image.Image:
    """Fallback: tạo gradient đẹp nếu Imagen fail"""
    img = Image.new("RGB", (COVER_W, COVER_H))
    draw = ImageDraw.Draw(img)

    gradients = {
        "Self-help":  [(255, 180, 50),  (200, 80, 20)],
        "Business":   [(15, 25, 60),    (40, 80, 160)],
        "Finance":    [(10, 50, 30),    (30, 120, 60)],
        "Health":     [(40, 160, 100),  (20, 80, 60)],
        "How-to":     [(50, 120, 200),  (20, 60, 140)],
        "default":    [(30, 30, 60),    (80, 40, 120)],
    }
    c1, c2 = gradients.get(niche, gradients["default"])

    for y in range(COVER_H):
        t = y / COVER_H
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (COVER_W, y)], fill=(r, g, b))

    return img


def get_font(size: int, bold: bool = False):
    """Lấy font — fallback về default nếu không có font file"""
    font_paths = [
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans-{'Bold' if bold else ''}.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def overlay_text(img: Image.Image, title: str, subtitle: str, author: str, niche: str) -> Image.Image:
    """Overlay title + author lên ảnh theo KDP layout đẹp"""
    img = img.resize((COVER_W, COVER_H), Image.LANCZOS)

    # Darkened overlay để chữ dễ đọc
    overlay = Image.new("RGBA", (COVER_W, COVER_H), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Bottom dark gradient (chỗ để title)
    for y in range(COVER_H // 2, COVER_H):
        alpha = int(180 * (y - COVER_H // 2) / (COVER_H // 2))
        draw_overlay.line([(0, y), (COVER_W, y)], fill=(0, 0, 0, alpha))

    # Top dark overlay nhẹ
    for y in range(0, COVER_H // 4):
        alpha = int(80 * (1 - y / (COVER_H // 4)))
        draw_overlay.line([(0, y), (COVER_W, y)], fill=(0, 0, 0, alpha))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    margin = 80

    # ── Niche badge (top left) ──
    badge_font = get_font(36)
    badge_text = niche.upper()
    draw.rectangle([margin, 80, margin + len(badge_text) * 22 + 30, 130], fill=(255, 255, 255, 180))
    draw.text((margin + 15, 88), badge_text, font=badge_font, fill=(20, 20, 20))

    # ── Title (big, bottom half) ──
    title_font = get_font(120, bold=True)
    title_words = title.split()
    # Wrap title manually
    lines, current = [], ""
    for word in title_words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=title_font)
        if bbox[2] > COVER_W - margin * 2:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    title_block_h = len(lines) * 140
    title_y = COVER_H - title_block_h - 280  # bottom area

    for line in lines:
        # Shadow
        draw.text((margin + 4, title_y + 4), line, font=title_font, fill=(0, 0, 0, 180))
        draw.text((margin, title_y), line, font=title_font, fill=(255, 255, 255))
        title_y += 140

    # ── Subtitle ──
    if subtitle:
        sub_font = get_font(52)
        draw.text((margin, title_y + 20), subtitle, font=sub_font, fill=(220, 220, 200))
        title_y += 70

    # ── Divider line ──
    draw.rectangle([margin, title_y + 40, margin + 100, title_y + 46], fill=(255, 200, 50))

    # ── Author ──
    auth_font = get_font(50)
    draw.text((margin, title_y + 60), f"by {author}", font=auth_font, fill=(200, 200, 200))

    return img


def make_cover(config: dict) -> Path | None:
    """Main function: tạo bìa sách và lưu file"""
    title    = config.get("title", "Untitled")
    subtitle = config.get("subtitle", "")
    author   = config.get("author", "Unknown Author")
    niche    = config.get("niche", "Self-help")

    if not PIL_OK:
        log("⚠ Pillow not installed — skipping cover generation")
        return None

    log(f"🎨 Generating cover for: {title}")
    out_path = OUTPUT_DIR / f"{title}_cover.jpg"

    # Step 1: Get image prompt from Gemini
    log("  → Asking Gemini for cover art prompt...")
    try:
        img_prompt = generate_cover_prompt(title, niche)
        log(f"  Prompt: {img_prompt[:80]}...")
    except Exception as e:
        log(f"  ⚠ Prompt generation failed: {e}")
        img_prompt = f"Professional {niche} book cover background, minimal, cinematic"

    # Step 2: Generate background image
    log("  → Generating background with Imagen...")
    bg_img = generate_image_gemini(img_prompt)

    if bg_img is None:
        log("  → Imagen unavailable, using gradient fallback")
        bg_img = create_gradient_background(niche)

    # Step 3: Overlay text
    log("  → Adding title & author overlay...")
    final = overlay_text(bg_img, title, subtitle, author, niche)

    # Step 4: Save
    final.save(str(out_path), "JPEG", quality=95)
    log(f"✓ Cover saved: {out_path} ({COVER_W}×{COVER_H}px)")
    return out_path
