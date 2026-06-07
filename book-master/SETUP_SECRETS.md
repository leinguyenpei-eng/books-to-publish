# 🔑 Hướng dẫn lấy API Keys

## 1. GEMINI_API_KEY ✅ (Bắt buộc — Miễn phí)
1. Vào: https://aistudio.google.com/apikey
2. Bấm **Create API Key**
3. Copy chuỗi bắt đầu bằng `AIzaSy...`

## 2. ANTHROPIC_API_KEY ✅ (Bắt buộc — Có phí, ~$5 thử nghiệm)
1. Vào: https://console.anthropic.com
2. Bấm **API Keys** → **Create Key**
3. Copy chuỗi bắt đầu bằng `sk-ant-...`

## 3. GITHUB_TOKEN (Cho Telegram Bot)
1. Vào: https://github.com/settings/tokens
2. **Generate new token (classic)**
3. Chọn scope: `repo` (toàn bộ)
4. Copy chuỗi bắt đầu bằng `ghp_...`

## 4. TELEGRAM_BOT_TOKEN
1. Nhắn @BotFather trên Telegram
2. Gõ `/newbot` → đặt tên bot
3. Copy token (dạng: `123456:ABC-def...`)

## 5. TELEGRAM_CHAT_ID
1. Nhắn @userinfobot trên Telegram
2. Nó sẽ reply số ID của bạn (dạng: `123456789`)

## 6. Các key tùy chọn (thêm sau khi có sale)
- **GUMROAD**: gumroad.com → Settings → Advanced → Application ID
- **PAYHIP**: payhip.com → Account → API Key
- **BEACONS**: beacons.ai → Settings → Integrations → API
- **FB_PAGE_TOKEN**: developers.facebook.com → App → Graph API Explorer

## Cách thêm vào GitHub
1. Vào repo GitHub của bạn
2. **Settings** → **Secrets and variables** → **Actions**
3. Bấm **New repository secret**
4. Điền tên (ví dụ `GEMINI_API_KEY`) và value → Save
