# 📚 Book Pipeline — Master Edition

Hệ thống tự động viết & publish sách từ YouTube.

## Luồng hoạt động

```
Telegram Bot (Oracle Cloud)
  → Bạn nhắn topic hoặc paste YouTube links
  → Gemini tạo 3 ý tưởng sách
  → Bạn chọn 1/2/3
  → Bot fetch transcripts (chạy trên Oracle Cloud — không bị YouTube block)
  → Push .yml lên GitHub

GitHub Actions (tự chạy ~35 phút)
  → Đọc transcript từ .yml
  → Gemini tổng hợp outline 12 chương
  → Claude Sonnet viết full sách (EN + VI)
  → Export DOCX chuẩn KDP 6×9"
  → Generate bìa sách (Pillow)
  → Auto-publish: Gumroad + Payhip + Beacons + Fourthwall + Etsy
  → Tạo GitHub Release để download
  → Telegram thông báo xong
```

## Setup (1 lần duy nhất)

### 1. Clone/upload repo lên GitHub
Tạo repo tên `my-books` (Private OK), upload toàn bộ folder này.

### 2. Thêm GitHub Secrets
Vào repo → Settings → Secrets and variables → Actions:

| Secret | Lấy từ đâu | Bắt buộc? |
|--------|-----------|-----------|
| `GEMINI_API_KEY` | aistudio.google.com/apikey | ✅ |
| `ANTHROPIC_API_KEY` | console.anthropic.com | ✅ |
| `GUMROAD_API_KEY` | gumroad.com → Settings → Advanced | Tùy chọn |
| `PAYHIP_API_KEY` | payhip.com → Account → API | Tùy chọn |
| `BEACONS_API_KEY` | beacons.ai → Settings → API | Tùy chọn |
| `FOURTHWALL_API_KEY` | fourthwall.com → Settings → API | Tùy chọn |
| `FB_PAGE_TOKEN` | Facebook Developer | Tùy chọn |
| `MAILCHIMP_API_KEY` | mailchimp.com → Account → API Keys | Tùy chọn |
| `SENDGRID_API_KEY` | sendgrid.com → Settings → API Keys | Tùy chọn |

> Chỉ cần GEMINI + ANTHROPIC là pipeline chạy được. Các key còn lại thêm sau khi có sale.

### 3. Chạy Telegram Bot trên Oracle Cloud

SSH vào máy ảo Oracle Cloud của bạn, rồi:

```bash
# Cài thư viện
pip3 install "python-telegram-bot[job-queue]==20.7" requests youtube-transcript-api yt-dlp PyGithub

# Tạo file .env
nano .env
```

Điền vào `.env`:
```
TELEGRAM_BOT_TOKEN=token_từ_BotFather
GEMINI_API_KEY=AIzaSy...
GITHUB_TOKEN=ghp_...
GITHUB_USERNAME=tên_github_của_bạn
GITHUB_REPO=my-books
AUTHOR_NAME=Tên Tác Giả
TELEGRAM_CHAT_ID=chat_id_của_bạn
```

```bash
# Chạy bot (background)
nohup python3 telegram_bot.py &
```

### 4. Dùng thôi!
Nhắn bot bất kỳ topic tiếng Anh, ví dụ:
- `habits for software developers`
- `passive income strategies 2024`
- Hoặc paste thẳng YouTube links

## Cấu trúc file

```
├── telegram_bot.py          ← Chạy trên Oracle Cloud
├── scripts/
│   ├── build_book.py        ← Script chính (GitHub Actions)
│   ├── transcript_fetcher.py
│   ├── cover_generator.py
│   ├── social_publisher.py
│   ├── multi_social.py
│   ├── email_marketing.py
│   ├── kdp_guide.py
│   └── publish_etsy.py
├── .github/workflows/
│   └── build-book.yml       ← GitHub Actions workflow
├── books/                   ← File .yml sách (bot tự tạo)
├── outputs/                 ← DOCX, cover, guide (GitHub Actions tạo)
├── config/
│   └── pricing.json
└── requirements.txt
```

## Fix đã áp dụng trong bản này

1. ✅ Gemini model → `gemini-2.0-flash` (fix lỗi 404)
2. ✅ Claude API timeout → 180s (fix lỗi Read timed out)
3. ✅ Gemini timeout → 180s (fix lỗi Read timed out)
4. ✅ OUTPUT_DIR dùng absolute path (fix lỗi khi chạy từ thư mục khác)
5. ✅ `Optional[X]` thay vì `X | Y` (fix Python 3.9 compatibility)
6. ✅ `python-telegram-bot[job-queue]` trong requirements (fix APScheduler crash)
7. ✅ `bot_state.json` persist state (fix mất queue khi restart)
8. ✅ GitHub run_id tracking (fix nhầm run khi chạy song song)
9. ✅ Xóa `build_single.py` (đã merge vào `build_book.py`)
10. ✅ Xóa `n8n-workflow.json` (không cần, telegram bot đã handle)
