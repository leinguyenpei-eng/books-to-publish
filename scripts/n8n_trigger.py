"""
n8n_trigger.py
Sau khi GitHub Actions build xong sách → trigger n8n webhook
để n8n tự động tạo bìa Canva + publish
"""

import os, requests, json
from pathlib import Path

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")  # GitHub Secret
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


def trigger_n8n(config: dict, docx_path: Path, buy_links: dict):
    """Gọi n8n webhook với thông tin sách vừa build xong"""
    if not N8N_WEBHOOK_URL:
        print("⚠ No N8N_WEBHOOK_URL secret — skipping n8n trigger")
        return

    payload = {
        "book_title":       config.get("title", "Untitled"),
        "book_subtitle":    config.get("subtitle", ""),
        "author_name":      config.get("author", "Unknown"),
        "book_category":    config.get("niche", "Self-help"),
        "short_description": config.get("description", ""),
        "price_usd":        config.get("price_usd", 9.99),
        "price_vnd":        config.get("price_vnd", 249000),
        "docx_filename":    docx_path.name,
        "buy_links":        buy_links,
        "languages":        config.get("languages", ["en", "vi"]),
    }

    print(f"📡 Triggering n8n for: {config.get('title')}")
    try:
        r = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        if r.status_code == 200:
            print(f"  ✓ n8n triggered successfully")
            result = r.json()
            if result.get("cover_url"):
                print(f"  🎨 Cover: {result['cover_url']}")
        else:
            print(f"  ⚠ n8n response: {r.status_code} — {r.text[:200]}")
    except Exception as e:
        print(f"  ⚠ n8n trigger failed: {e}")
