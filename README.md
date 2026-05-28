# 📚 YouTube → Book Pipeline

Tự động viết sách từ YouTube links → xuất DOCX chuẩn KDP → publish Gumroad/Payhip.  
Chạy hoàn toàn trên **GitHub Actions** — không cần máy tính online.

---

## 🚀 Bắt đầu nhanh

### Bước 1 — Thêm GitHub Secrets
Vào repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Lấy ở đâu | Bắt buộc? |
|---|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | ✅ Bắt buộc |
| `ANTHROPIC_API_KEY` | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) | ✅ Bắt buộc |
| `GUMROAD_API_KEY` | Gumroad → Settings → Advanced → API | Tùy chọn |
| `PAYHIP_API_KEY` | Payhip → Settings → API | Tùy chọn |
| `BEACONS_API_KEY` | Beacons.ai → Settings → API | Tùy chọn |
| `FOURTHWALL_API_KEY` | Fourthwall → Settings → API Keys | Tùy chọn |
| `FB_PAGE_TOKEN` | Meta Business Suite → Page Access Token | Tùy chọn |
| `FB_PAGE_ID` | Facebook Page → About → Page ID | Tùy chọn |
| `MAILCHIMP_API_KEY` | Mailchimp → Account → API Keys | Tùy chọn |
| `MAILCHIMP_SERVER` | Prefix cuối API key (vd: `us1`) | Tùy chọn |
| `MAILCHIMP_LIST_ID` | Mailchimp → Audience → Settings → Audience ID | Tùy chọn |
| `SENDGRID_API_KEY` | SendGrid → Settings → API Keys | Tùy chọn |
| `FROM_EMAIL` | Email gửi đi | Tùy chọn |
| `FROM_NAME` | Tên hiển thị email | Tùy chọn |
| `PROXY_URL` | `socks5://user:pass@host:port` nếu YouTube bị block | Tùy chọn |
| `SCRAPER_API_KEY` | [scraperapi.com](https://scraperapi.com) — 1000 req/tháng free | Tùy chọn |

### Bước 2 — Tạo file sách
Mỗi cuốn sách = 1 file `.yml` trong thư mục `books/`. Xem mẫu `books/01-self-help-mindset.yml`.

```yaml
title: "Tên Sách"
subtitle: "Subtitle"
author: "Tên Tác Giả"
niche: "Self-help"   # Self-help | Business | Finance | Health | How-to
languages:
  - en
  - vi
price_usd: 9.99
price_vnd: 249000
description: "Mô tả 1-2 câu."
youtube_urls:
  - https://www.youtube.com/watch?v=VIDEO_ID
  # Thêm 10-20 links
```

### Bước 3 — Chạy pipeline
- **Thủ công:** Tab **Actions** → **📚 Auto Book Builder** → **Run workflow**
- **Tự động:** Mỗi Thứ Hai 9PM giờ Houston (cron `0 2 * * 1` UTC)

### Bước 4 — Download kết quả
Tab **Actions** → lần chạy mới nhất → **Artifacts** → download ZIP

---

## 💰 Chi phí

| Dịch vụ | Chi phí |
|---|---|
| GitHub Actions | **Miễn phí** (2,000 phút/tháng) |
| Gemini API (Flash) | **Miễn phí** |
| Claude API (Sonnet) | ~$0.20/sách |
| YouTube Transcript | **Miễn phí** |

---

## 🔄 Workflow tổng quan

```
YouTube URLs (10-20 links)
    ↓ transcript_fetcher.py — yt-dlp + 5 fallback APIs
Raw transcripts
    ↓ Gemini — tổng hợp JSON outline 12 chương
Book outline
    ↓ Claude Sonnet — viết 3 section × 12 chương
Manuscript EN + VI (~25,000 words mỗi bản)
    ↓ python-docx — KDP 6×9" format
.docx files
    ↓ cover_generator.py — Gemini Imagen + Pillow
Cover image (1600×2560px)
    ↓ Gumroad / Payhip / Beacons / Fourthwall API
Published (tự động)
    ↓ social_publisher.py + multi_social.py
Facebook / TikTok / Instagram / LinkedIn / Twitter content
    ↓ email_marketing.py — Mailchimp / SendGrid
Email campaign
```

---

## ❓ Troubleshooting

**"No transcripts fetched"** → Video tắt caption. Script fallback qua 6 methods. Thêm `SCRAPER_API_KEY` hoặc `PROXY_URL` nếu cần.

**Claude 401 Unauthorized** → Kiểm tra `ANTHROPIC_API_KEY` trong Secrets + số dư tại console.anthropic.com.

**Gemini 429 Rate Limit** → Script tự retry. Nếu vẫn lỗi: nâng Gemini Pay-as-you-go hoặc chạy từng sách một.

**Cover không generate** → Gemini Imagen cần quota riêng. Script fallback về gradient màu tự động.

**DOCX trống** → Xem logs → dòng "DOCX saved". Nếu không có: Claude hết tiền hoặc bị rate limit.
