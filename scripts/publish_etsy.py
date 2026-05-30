"""
publish_etsy.py — Auto-publish to Etsy via Open API v3
Docs: https://developers.etsy.com/documentation
"""
import os, json, requests, sys
from pathlib import Path
from datetime import datetime

API_KEY       = os.environ.get("ETSY_API_KEY", "")
REFRESH_TOKEN = os.environ.get("ETSY_REFRESH_TOKEN", "")
SHOP_ID       = os.environ.get("ETSY_SHOP_ID", "")
OUTPUT_DIR    = Path(__file__).parent.parent / "outputs"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def get_access_token() -> str:
    r = requests.post(
        "https://api.etsy.com/v3/public/oauth/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "client_id": API_KEY,
              "refresh_token": REFRESH_TOKEN},
        timeout=30
    )
    if r.status_code != 200:
        raise RuntimeError(f"Etsy token refresh failed: {r.text[:200]}")
    return r.json()["access_token"]


def publish_to_etsy(docx_path: Path, config: dict, cover_path: Path = None) -> str:
    if not all([API_KEY, REFRESH_TOKEN, SHOP_ID]):
        log("⚠ Etsy credentials missing (ETSY_API_KEY / ETSY_REFRESH_TOKEN / ETSY_SHOP_ID)")
        return ""

    title       = config.get("title", "Untitled")
    subtitle    = config.get("subtitle", "")
    description = config.get("description", "")
    price       = float(config.get("price_usd", 9.99))
    niche       = config.get("niche", "Self-help")

    # Etsy tags from config or generated
    tags = config.get("etsy_tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    tags = [t[:20] for t in tags if t][:13]   # Etsy max 13 tags, 20 chars each

    # If no tags, build basic ones from niche
    if not tags:
        tags = [niche.lower(), "ebook", "digital download", "self help",
                "instant download", "pdf book", "digital book"][:13]

    log(f"📤 Publishing to Etsy: {title}")

    try:
        access_token = get_access_token()
    except Exception as e:
        log(f"  ❌ {e}")
        return ""

    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    etsy_desc = f"""{description}

📖 WHAT YOU GET:
• Instant digital download (DOCX + PDF format)
• Print-ready, high-quality content
• Compatible with Word, Google Docs, and PDF readers

✨ PERFECT FOR:
• Personal development and growth
• Learning and skill-building
• Thoughtful gifts

⚡ INSTANT DELIVERY:
1. Complete your purchase
2. Download link sent immediately
3. Start reading right away!

© {config.get('author', 'Your Brand')} — All Rights Reserved"""

    listing_data = {
        "quantity": 999,
        "title": f"{title}: {subtitle}"[:140],
        "description": etsy_desc,
        "price": price,
        "who_made": "i_did",
        "when_made": "made_to_order",
        "taxonomy_id": 2078,
        "tags": tags,
        "is_digital": True,
        "type": "download"
    }

    resp = requests.post(
        f"https://openapi.etsy.com/v3/application/shops/{SHOP_ID}/listings",
        headers=headers, json=listing_data, timeout=30
    )

    if resp.status_code not in (200, 201):
        log(f"  ❌ Listing failed {resp.status_code}: {resp.text[:200]}")
        return ""

    listing    = resp.json()
    listing_id = listing.get("listing_id", "")
    url        = f"https://www.etsy.com/listing/{listing_id}"
    log(f"  ✓ Listing created: {url}")

    # Upload DOCX file
    if docx_path and docx_path.exists() and listing_id:
        with open(docx_path, "rb") as f:
            file_resp = requests.post(
                f"https://openapi.etsy.com/v3/application/shops/{SHOP_ID}/listings/{listing_id}/files",
                headers={"Authorization": f"Bearer {access_token}", "x-api-key": API_KEY},
                files={"file": (docx_path.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                timeout=120
            )
        log(f"  {'✓' if file_resp.status_code in (200,201) else '⚠️'} File upload: {file_resp.status_code}")

    # Upload cover image
    if cover_path and cover_path.exists() and listing_id:
        with open(cover_path, "rb") as f:
            img_resp = requests.post(
                f"https://openapi.etsy.com/v3/application/shops/{SHOP_ID}/listings/{listing_id}/images",
                headers={"Authorization": f"Bearer {access_token}", "x-api-key": API_KEY},
                files={"image": ("cover.jpg", f, "image/jpeg")},
                data={"rank": 1},
                timeout=60
            )
        log(f"  {'✓' if img_resp.status_code in (200,201) else '⚠️'} Image upload: {img_resp.status_code}")

    log(f"  ✅ Etsy: {url} — ${price}")
    return url
