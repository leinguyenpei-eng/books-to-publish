# 🔑 Hướng dẫn thêm Secrets vào GitHub

## Cách vào trang Secrets
1. Vào repo `my-books` trên GitHub
2. Click tab **Settings** (góc trên cùng)
3. Menu trái → **Secrets and variables** → **Actions**
4. Click **New repository secret** → điền từng cái theo bảng dưới

---

## ✅ BẮT BUỘC — Pipeline không chạy nếu thiếu

### GEMINI_API_KEY
- Lấy tại: https://aistudio.google.com/apikey
- Format: `AIzaSy...` (39 ký tự)
- Miễn phí hoàn toàn

### ANTHROPIC_API_KEY
- Lấy tại: https://console.anthropic.com/settings/keys
- Format: `sk-ant-api03-...`
- Chi phí: ~$0.20/sách (nạp $10 dùng được ~50 sách)

---

## 🟡 TÙY CHỌN — Publish tự động

### GUMROAD_API_KEY
- Lấy tại: Gumroad → Settings → Advanced → API Application
- Bấm "Create application" → copy Access Token

### PAYHIP_API_KEY
- Lấy tại: Payhip → Settings → Integrations → API

### FB_PAGE_TOKEN + FB_PAGE_ID
- Vào: https://business.facebook.com
- Chọn trang → Settings → Page Access Tokens
- FB_PAGE_ID: vào trang Facebook → About → cuộn xuống cuối → Page ID

---

## 🟡 TÙY CHỌN — Email marketing

### MAILCHIMP_API_KEY
- Lấy tại: Mailchimp → Account → Extras → API Keys → Create A Key
- Format: `xxxxxxxx-us1` (phần sau dấu gạch là server)

### MAILCHIMP_SERVER
- Chính là phần suffix trong API key
- Ví dụ: API key `abc123def-us21` → MAILCHIMP_SERVER = `us21`

### MAILCHIMP_LIST_ID
- Mailchimp → Audience → Manage Audience → Settings → Audience ID

### FROM_EMAIL + FROM_NAME
- Email và tên bạn muốn gửi đi
- Ví dụ: `hello@yoursite.com` và `Alex Morgan`

---

## 🟡 TÙY CHỌN — Nếu YouTube bị block

### SCRAPER_API_KEY
- Đăng ký miễn phí tại: https://scraperapi.com
- Free plan: 1000 requests/tháng

### PROXY_URL
- Nếu bạn có proxy riêng
- Format: `socks5://username:password@host:port`

---

## ⚠️ Lưu ý quan trọng
- Tên Secret phải gõ **CHÍNH XÁC** — có phân biệt HOA/thường
- `GEMINI_API_KEY` ✅ đúng | `gemini_api_key` ❌ sai
- Sau khi lưu, không ai đọc lại được giá trị — kể cả bạn
- Nếu nhập sai: xóa và tạo lại
