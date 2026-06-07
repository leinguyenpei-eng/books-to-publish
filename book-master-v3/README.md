# 📚 Book Generator — Master Version

> Combine tất cả tinh hoa từ mọi version trước.  
> Không bao giờ timeout. Không bao giờ Gemini exhausted.  
> Email sau mỗi chương. Publish tự động Gumroad + Payhip.

---

## Workflow

```
[Bạn] Paste YouTube links vào NotebookLM (thủ công — 2 phút)
         ↓ copy text → paste vào books/<slug>/transcript.txt → git push
         
Job 1 — Gemini tạo outline 12 chương (~30s)
         → Email báo outline xong
         
Job 2 — Claude viết từng chương (matrix, sequential)
  Ch.1 → email ✉ → Ch.2 → email ✉ → ... → Ch.12 → email ✉
  Mỗi chương = 1 job riêng → không bao giờ timeout
  Mỗi chương ~2,100-2,500 words (3 sections x 700w)
         
Job 3 — Finalize
  Claude viết Intro + Conclusion
  Export DOCX KDP 6×9"
  Tạo bìa (Pollinations AI background + Pillow overlay)
  Publish Gumroad + Payhip tự động
  Email DOCX đầy đủ
  Telegram thông báo kèm ảnh bìa + links
  GitHub Release để download
```

**Tại sao không timeout?**
- Mỗi chapter = 1 GitHub Actions job riêng = max 15 phút
- Job 3 chỉ viết Intro + Conclusion = max 30 phút
- Không bao giờ viết cả cuốn trong 1 lần

**Tại sao không bị Gemini exhausted?**
- Gemini chỉ dùng 1 lần duy nhất (tạo outline)
- Claude viết 100% nội dung sách
- NotebookLM bóc transcript miễn phí, không quota

---

## Setup (1 lần duy nhất)

### 1. Thêm GitHub Secrets

Vào repo → **Settings** → **Secrets and variables** → **Actions**:

| Secret | Bắt buộc? | Lấy từ đâu |
|--------|-----------|-----------|
| `ANTHROPIC_API_KEY` | ✅ | console.anthropic.com |
| `GEMINI_API_KEY` | ✅ | aistudio.google.com/apikey |
| `GMAIL_USER` | ✅ | địa chỉ Gmail của bạn |
| `GMAIL_APP_PASSWORD` | ✅ | myaccount.google.com → Security → App Passwords |
| `GMAIL_TO` | ✅ | email nhận chương (có thể giống GMAIL_USER) |
| `TELEGRAM_BOT_TOKEN` | Khuyên dùng | @BotFather trên Telegram |
| `TELEGRAM_CHAT_ID` | Khuyên dùng | @userinfobot trên Telegram |
| `GUMROAD_API_KEY` | Tùy chọn | gumroad.com → Settings → Advanced |
| `PAYHIP_API_KEY` | Tùy chọn | payhip.com → Account → API Key |

### 2. Lấy Gmail App Password

1. Vào myaccount.google.com → **Security**
2. Bật **2-Step Verification** (nếu chưa bật)
3. **App passwords** → Create → đặt tên "Book Bot"
4. Copy 16 ký tự (dạng: `xxxx xxxx xxxx xxxx`)

---

## Dùng thế nào

### Cách 1 — Qua GitHub Actions UI (dễ nhất)

1. Vào repo → tab **Actions**
2. Click **📚 Book Generator — Master Version**
3. Click **Run workflow**
4. Điền topic, category, author, email
5. Bấm **Run workflow** → ngồi đợi nhận email từng chương!

### Cách 2 — Paste transcript từ NotebookLM (chất lượng cao hơn)

1. Vào **notebooklm.google.com**
2. **New Notebook** → **Add sources** → **YouTube** → paste links
3. Chờ xử lý → chat box gõ:
   ```
   Summarize all key insights, frameworks, case studies, and stories 
   from these sources in comprehensive detail. Include specific 
   examples, data points, and quotes.
   ```
4. Copy toàn bộ câu trả lời
5. Paste vào `books/my-first-book/transcript.txt`
6. `git add . && git commit -m "Add transcript" && git push`
7. Actions tự chạy!

---

## Cấu trúc

```
├── scripts/
│   ├── step1_research.py    ← Gemini tạo outline
│   ├── step2_write_chapter.py ← Claude viết 1 chương
│   └── step3_finalize.py    ← Assemble + Cover + Publish
├── .github/workflows/
│   └── build-book.yml       ← GitHub Actions (3 jobs)
├── books/
│   └── my-first-book/
│       ├── config.yml       ← Thông tin sách
│       └── transcript.txt   ← Paste từ NotebookLM
├── output/                  ← GitHub Actions tạo
│   ├── outline.json
│   ├── chapter_01.txt ... chapter_12.txt
│   ├── <title>_KDP.docx
│   ├── <title>_cover.png
│   └── UPLOAD_GUIDE.txt
└── requirements.txt
```

---

## Tinh hoa từ mọi version

| Feature | Nguồn |
|---------|-------|
| 3-section chapter writing (open/middle/close) | pipeline-merged |
| Anti-AI voice system prompt | book-final |
| Email per chapter | generate_book_v2.yml |
| Job matrix sequential (no timeout) | generate_book_v2.yml |
| Pollinations AI cover background | book-automation |
| Pillow text overlay with themes | book-automation |
| DOCX export KDP 6×9" | book-final |
| Publish Gumroad + Payhip | book-automation |
| Telegram final summary + cover image | book-automation |
| Gemini outline only (not writing) | all versions |
| NotebookLM transcript (no YouTube block) | v2 |
| GitHub Release artifact | book-final |
