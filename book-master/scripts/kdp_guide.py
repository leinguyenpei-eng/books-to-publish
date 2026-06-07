"""
kdp_guide.py — Generate upload guides for KDP, Kobo, Google Play, Apple Books, B&N, Lulu
Called automatically after publishing to Gumroad/Payhip/Etsy.
"""
import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def generate_upload_guide(docx_path: Path, config: dict, cover_path: Path,
                           buy_links: dict, pricing: dict = None):
    """Generate UPLOAD_GUIDE.txt with metadata + platform instructions."""
    title    = config.get("title", "Untitled")
    subtitle = config.get("subtitle", "")
    author   = config.get("author", "Your Name")
    desc     = config.get("description", "")
    keywords = config.get("keywords", [])
    price    = config.get("price_usd", 9.99)

    p = pricing or {}

    lines = [
        "=" * 60,
        f"UPLOAD GUIDE — {title}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 60,
        "",
        "FILES READY:",
        f"  Manuscript: {docx_path.name if docx_path else 'book.docx'}",
        f"  Cover:      {cover_path.name if cover_path else 'cover.jpg'}",
        "",
        "BOOK METADATA (copy-paste):",
        f"  Title:       {title}",
        f"  Subtitle:    {subtitle}",
        f"  Author:      {author}",
        f"  Description: {desc}",
        f"  Keywords:    {', '.join(keywords[:7]) if keywords else '(add manually)'}",
        "",
        "AUTO-PUBLISHED ✅:",
    ]

    for platform, url in buy_links.items():
        if url:
            lines.append(f"  {platform}: {url}")

    lines += [
        "",
        "=" * 60,
        "MANUAL UPLOAD PLATFORMS:",
        "=" * 60,
        "",
        "1. AMAZON KDP — kdp.amazon.com",
        f"   Price: ${p.get('kdp', {}).get('price', price)} (70% royalty)",
        "   Steps: Bookshelf → + Kindle eBook → upload DOCX + cover.jpg",
        "   Note: approval takes 24-72 hours",
        "",
        "2. KOBO WRITING LIFE — kobo.com/writinglife",
        f"   Price: ${p.get('kobo', {}).get('price', price)} (70% royalty, 190+ countries)",
        "   Steps: Dashboard → New Title → upload DOCX + cover.jpg",
        "",
        "3. GOOGLE PLAY BOOKS — play.google.com/books/publish",
        f"   Price: ${p.get('google_play', {}).get('price', price)} (70% royalty + 7% affiliate)",
        "   Steps: Add Book → upload EPUB/DOCX + cover.jpg",
        "   Note: 3 billion Android users",
        "",
        "4. APPLE BOOKS — authors.apple.com",
        f"   Price: ${p.get('apple_books', {}).get('price', price)} (70% royalty)",
        "   Steps: My Books → New Book → upload EPUB + cover.jpg",
        "   Note: Pre-orders count toward launch day rankings!",
        "",
        "5. BARNES & NOBLE PRESS — press.barnesandnoble.com",
        f"   Price: ${p.get('bn_press', {}).get('price', price)} (70% royalty)",
        "   Steps: Publish → eBook → upload EPUB + cover.jpg",
        "",
        "6. LULU — lulu.com",
        f"   Price: ${p.get('lulu', {}).get('price', price+5)} (75% royalty direct)",
        "   Steps: Create → eBook or Print → upload PDF + cover.jpg",
        "   Note: Also distributes to Amazon, B&N automatically",
        "",
        "=" * 60,
        "SUGGESTED LAUNCH ORDER:",
        "  Day 1: KDP (largest audience) + Etsy ✅ + Gumroad ✅ + Payhip ✅",
        "  Day 2: Kobo + Google Play Books",
        "  Day 3: Apple Books (set pre-order!)",
        "  Day 5: B&N Press + Lulu",
        "=" * 60,
    ]

    out_path = OUTPUT_DIR / f"{title}_UPLOAD_GUIDE.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"✓ Upload guide saved: {out_path}")
    return out_path
