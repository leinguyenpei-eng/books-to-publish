# ✅ CHECKLIST — Làm theo thứ tự, xong bước nào tick bước đó

---

## PHASE 1 — Setup GitHub (làm 1 lần duy nhất)

- [ ] Vào **github.com** → đăng nhập
- [ ] Bấm **+** góc trên phải → **New repository**
- [ ] Đặt tên: `my-books` → chọn **Private** → bấm **Create repository**
- [ ] Giải nén file `book-master-v3-humanized.zip`
- [ ] Kéo thả toàn bộ nội dung bên trong vào trang GitHub repo vừa tạo
- [ ] Bấm **Commit changes**

---

## PHASE 2 — Lấy API Keys (làm 1 lần duy nhất)

### 🔑 Key 1 — Gemini (miễn phí)
- [ ] Vào **aistudio.google.com/apikey**
- [ ] Bấm **Create API key** → copy chuỗi `AIzaSy...`

### 🔑 Key 2 — Anthropic/Claude (có phí, ~$5 để test)
- [ ] Vào **console.anthropic.com**
- [ ] Bấm **API Keys** → **Create Key** → copy chuỗi `sk-ant-...`

### 📧 Key 3 — Gmail App Password (để nhận chương sách qua email)
- [ ] Vào **myaccount.google.com** → **Security**
- [ ] Bật **2-Step Verification** (nếu chưa bật)
- [ ] Tìm **App passwords** → **Create** → đặt tên "Book Bot"
- [ ] Copy 16 ký tự (dạng: `xxxx xxxx xxxx xxxx`)

### 📱 Key 4 — Telegram (để nhận thông báo, không bắt buộc)
- [ ] Mở Telegram → tìm **@BotFather** → gõ `/newbot` → đặt tên → copy token
- [ ] Tìm **@userinfobot** → gõ `/start` → copy số ID

---

## PHASE 3 — Thêm Keys vào GitHub

- [ ] Vào repo `my-books` → **Settings** → **Secrets and variables** → **Actions**
- [ ] Bấm **New repository secret** → thêm lần lượt:

| Tên Secret | Giá trị |
|-----------|---------|
| `GEMINI_API_KEY` | Key từ aistudio |
| `ANTHROPIC_API_KEY` | Key từ Anthropic |
| `GMAIL_USER` | your@gmail.com |
| `GMAIL_APP_PASSWORD` | 16 ký tự app password |
| `GMAIL_TO` | email nhận sách (giống GMAIL_USER cũng được) |
| `TELEGRAM_BOT_TOKEN` | Token từ BotFather (nếu có) |
| `TELEGRAM_CHAT_ID` | ID từ userinfobot (nếu có) |
| `GUMROAD_API_KEY` | Từ gumroad.com → Settings → Advanced (thêm sau) |
| `PAYHIP_API_KEY` | Từ payhip.com → Account → API (thêm sau) |

> Chỉ cần `GEMINI_API_KEY` + `ANTHROPIC_API_KEY` + `GMAIL_USER` + `GMAIL_APP_PASSWORD` là chạy được. Còn lại thêm sau.

---

## PHASE 4 — Lấy transcript từ NotebookLM (làm mỗi lần viết sách mới)

- [ ] Vào **notebooklm.google.com** → đăng nhập Gmail
- [ ] Bấm **New Notebook**
- [ ] Bấm **Add sources** → chọn **YouTube** → paste các link YouTube vào (tối đa 50 link)
- [ ] Chờ 2-3 phút để xử lý
- [ ] Ở ô chat bên phải, paste đúng đoạn này:

```
Summarize all key insights, frameworks, case studies, and stories 
from these sources in comprehensive detail. Include specific examples, 
data points, and quotes.
```

- [ ] Copy toàn bộ câu trả lời
- [ ] Mở file `books/my-first-book/transcript.txt` trong repo GitHub
- [ ] Xóa nội dung cũ → paste nội dung vừa copy vào → **Commit changes**

---

## PHASE 5 — Chạy để viết sách

- [ ] Vào repo `my-books` → tab **Actions**
- [ ] Bấm **📚 Book Generator — Master Version** ở menu trái
- [ ] Bấm **Run workflow** (góc phải)
- [ ] Điền thông tin:
  - **Book topic**: ví dụ `habits for software developers`
  - **Category**: chọn từ danh sách
  - **Author name**: tên bạn muốn
  - **Email**: email nhận chương sách
  - **Writing style**: ví dụ `James Clear` hoặc `Malcolm Gladwell`
- [ ] Bấm **Run workflow** màu xanh

---

## PHASE 6 — Nhận sách

- [ ] Sau mỗi chương xong (~8 phút/chương) → nhận email chứa nội dung chương đó
- [ ] Sau tất cả 12 chương xong (~2 tiếng) → nhận email chứa file DOCX đầy đủ kèm link Gumroad/Payhip
- [ ] Vào repo → tab **Actions** → click vào run vừa chạy → kéo xuống **Artifacts** → download ZIP
- [ ] Trong ZIP có: `*.docx`, `*_cover.png`, `UPLOAD_GUIDE.txt`

---

## PHASE 7 — Upload lên KDP (thủ công, ~10 phút)

- [ ] Vào **kdp.amazon.com** → **Bookshelf** → **Create** → **eBook**
- [ ] Mở file `UPLOAD_GUIDE.txt` (trong ZIP) → copy thông tin từ đó điền vào KDP
- [ ] Upload file DOCX → Upload ảnh bìa PNG
- [ ] Set giá → **Publish**

---

## 🔁 Lần sau muốn viết sách mới

Chỉ cần lặp lại **Phase 4** và **Phase 5** — toàn bộ setup đã xong rồi.

---

## ❓ Hay bị hỏi

**Sách lưu ở đâu?**
→ GitHub repo → tab **Releases** → download bất kỳ lúc nào (vĩnh viễn)

**Mất bao lâu?**
→ ~2 tiếng cho 12 chương. Bạn không cần làm gì trong thời gian đó.

**Tốn bao nhiêu tiền?**
→ Mỗi cuốn sách ~$1-2 tiền Claude API. Gemini và NotebookLM miễn phí.

**Gemini bị rate limit thì sao?**
→ Pipeline tự retry. Nếu vẫn fail thì chờ 1 tiếng rồi Run lại — quota reset theo giờ.
