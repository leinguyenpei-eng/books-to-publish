"""
email_marketing.py
Tự động gửi email announce sách mới tới subscriber list.
Hỗ trợ: Mailchimp (free 500 contacts) + SendGrid (free 100/day)
Fallback: lưu email draft ra file .html để gửi thủ công
"""

import os, requests, json, base64
from pathlib import Path
from datetime import datetime

MAILCHIMP_KEY    = os.environ.get("MAILCHIMP_API_KEY", "")
MAILCHIMP_SERVER = os.environ.get("MAILCHIMP_SERVER", "us1")   # vd: us1, us21
MAILCHIMP_LIST   = os.environ.get("MAILCHIMP_LIST_ID", "")
SENDGRID_KEY     = os.environ.get("SENDGRID_API_KEY", "")
FROM_EMAIL       = os.environ.get("FROM_EMAIL", "your@email.com")
FROM_NAME        = os.environ.get("FROM_NAME", "Your Name")
OUTPUT_DIR       = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── Build email HTML ──────────────────────────────────────────────────────────
def build_email_html(config: dict, buy_links: dict, cover_path: Path = None) -> tuple:
    """Tạo email HTML đẹp cho launch announcement"""
    title       = config.get("title", "Untitled")
    subtitle    = config.get("subtitle", "")
    author      = config.get("author", "Unknown")
    description = config.get("description", "")
    price_usd   = config.get("price_usd", 9.99)
    niche       = config.get("niche", "Self-help")

    # Build buy buttons HTML
    buttons_html = ""
    platform_colors = {
        "Gumroad":    "#ff90e8",
        "Payhip":     "#4353ff",
        "Beacons":    "#7c3aed",
        "Fourthwall": "#f59e0b",
    }
    for platform, url in buy_links.items():
        if url:
            color = platform_colors.get(platform, "#333333")
            buttons_html += f"""
            <a href="{url}" style="
                display:inline-block; margin:8px; padding:14px 28px;
                background:{color}; color:white; text-decoration:none;
                border-radius:8px; font-weight:bold; font-size:16px;">
                Buy on {platform} — ${price_usd}
            </a>"""

    if not buttons_html:
        buttons_html = "<p><em>Buy links coming soon!</em></p>"

    # Cover image embed (base64 if local, or placeholder)
    cover_html = ""
    if cover_path and cover_path.exists():
        with open(cover_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        cover_html = f"""
        <img src="data:image/jpeg;base64,{img_b64}"
             alt="Book cover: {title}"
             style="max-width:200px; border-radius:8px;
                    box-shadow:0 8px 24px rgba(0,0,0,0.15);">"""

    subject = f"📚 New Book: {title} — Just Published!"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
</head>
<body style="margin:0; padding:0; background:#f5f5f5; font-family:Georgia, serif;">

<div style="max-width:600px; margin:40px auto; background:white;
            border-radius:16px; overflow:hidden;
            box-shadow:0 4px 24px rgba(0,0,0,0.08);">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);
              padding:40px 40px 30px; text-align:center;">
    <p style="color:#aaa; font-size:12px; letter-spacing:2px;
              text-transform:uppercase; margin:0 0 12px;">
      New Release · {niche}
    </p>
    <h1 style="color:white; font-size:28px; margin:0 0 8px; line-height:1.3;">
      {title}
    </h1>
    {f'<p style="color:#ccc; font-size:16px; margin:0;">{subtitle}</p>' if subtitle else ''}
    <p style="color:#888; font-size:14px; margin:16px 0 0;">by {author}</p>
  </div>

  <!-- Cover + Description -->
  <div style="padding:40px; text-align:center;">
    {cover_html}

    <p style="color:#444; font-size:16px; line-height:1.8;
              margin:24px 0; text-align:left;">
      {description}
    </p>

    <!-- Buy buttons -->
    <div style="margin:32px 0; text-align:center;">
      <p style="color:#888; font-size:13px; margin:0 0 16px;">
        Available now on multiple platforms:
      </p>
      {buttons_html}
    </div>

    <!-- What's inside teaser -->
    <div style="background:#f9f9f9; border-radius:12px;
                padding:24px; margin:24px 0; text-align:left;">
      <h3 style="color:#333; margin:0 0 12px; font-size:18px;">
        What you'll learn:
      </h3>
      <ul style="color:#555; line-height:2; margin:0; padding-left:20px;">
        <li>Proven strategies from 10+ expert sources</li>
        <li>12 chapters of actionable insights</li>
        <li>Available in English and Vietnamese</li>
        <li>25,000+ words of practical content</li>
      </ul>
    </div>
  </div>

  <!-- Footer -->
  <div style="background:#f5f5f5; padding:24px 40px;
              text-align:center; border-top:1px solid #eee;">
    <p style="color:#999; font-size:12px; margin:0;">
      You're receiving this because you subscribed to book updates.<br>
      <a href="{{unsubscribe_url}}" style="color:#999;">Unsubscribe</a>
    </p>
  </div>

</div>
</body>
</html>"""

    return subject, html


# ── Send via Mailchimp ────────────────────────────────────────────────────────
def send_mailchimp(subject: str, html: str, config: dict) -> bool:
    if not MAILCHIMP_KEY or not MAILCHIMP_LIST:
        log("⚠ No Mailchimp config — skip"); return False

    log("📧 Sending via Mailchimp...")
    base_url = f"https://{MAILCHIMP_SERVER}.api.mailchimp.com/3.0"
    auth = ("anystring", MAILCHIMP_KEY)

    # Create campaign
    r = requests.post(f"{base_url}/campaigns",
        auth=auth,
        json={
            "type": "regular",
            "recipients": {"list_id": MAILCHIMP_LIST},
            "settings": {
                "subject_line": subject,
                "from_name": FROM_NAME,
                "reply_to": FROM_EMAIL,
                "title": f"Campaign: {config.get('title','')}",
            }
        })
    data = r.json()
    if "id" not in data:
        log(f"  ⚠ Mailchimp campaign create failed: {data}")
        return False

    campaign_id = data["id"]

    # Set content
    requests.put(f"{base_url}/campaigns/{campaign_id}/content",
        auth=auth,
        json={"html": html})

    # Send
    r2 = requests.post(f"{base_url}/campaigns/{campaign_id}/actions/send", auth=auth)
    if r2.status_code == 204:
        log("  ✓ Mailchimp campaign sent!")
        return True
    log(f"  ⚠ Mailchimp send failed: {r2.text}")
    return False


# ── Send via SendGrid ─────────────────────────────────────────────────────────
def send_sendgrid(subject: str, html: str, config: dict,
                  recipient_emails: list = None) -> bool:
    if not SENDGRID_KEY:
        log("⚠ No SENDGRID_API_KEY — skip"); return False

    # If no list provided, send to FROM_EMAIL as test
    recipients = recipient_emails or [FROM_EMAIL]
    log(f"📧 Sending via SendGrid to {len(recipients)} recipients...")

    r = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {SENDGRID_KEY}",
                 "Content-Type": "application/json"},
        json={
            "from": {"email": FROM_EMAIL, "name": FROM_NAME},
            "subject": subject,
            "content": [{"type": "text/html", "value": html}],
            "personalizations": [
                {"to": [{"email": e}]} for e in recipients
            ]
        })

    if r.status_code == 202:
        log("  ✓ SendGrid sent!")
        return True
    log(f"  ⚠ SendGrid failed: {r.text}")
    return False


# ── Main entry ────────────────────────────────────────────────────────────────
def run_email_campaign(config: dict, buy_links: dict, cover_path: Path = None):
    title = config.get("title", "Untitled")
    log(f"\n📧 Email campaign: {title}")

    subject, html = build_email_html(config, buy_links, cover_path)

    # Save HTML draft always (fallback for manual sending)
    draft_path = OUTPUT_DIR / f"{title}_email_draft.html"
    draft_path.write_text(html, encoding="utf-8")
    log(f"  ✓ Email draft saved: {draft_path}")

    # Try Mailchimp first
    sent = send_mailchimp(subject, html, config)

    # Fallback to SendGrid
    if not sent:
        send_sendgrid(subject, html, config)
