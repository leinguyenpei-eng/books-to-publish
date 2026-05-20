# 📚 YouTube → Book Publisher

Tự động viết sách từ YouTube links → publish Gumroad + Payhip.  
Chạy hoàn toàn trên GitHub — không cần máy tính online.

---

## 🗂️ Cấu trúc thư mục

```
my-books/
├── .github/
│   └── workflows/
│       └── build-book.yml     ← GitHub Actions tự chạy ở đây
├── books/
│   └── example-book.yml       ← Mỗi quyển sách = 1 file .yml
├── scripts/
│   └── build_book.py          ← Code pipeline chính
└── outputs/                   ← File DOCX/PDF xuất ra đây
```

---

## 🚀 Hướng dẫn setup từng bước

### Bước 1 — Thêm API keys vào GitHub Secrets

API keys KHÔNG được để trong code (bảo mật). GitHub có chỗ lưu riêng gọi là **Secrets**.

1. Vào repo `my-books` trên GitHub
2. Click **Settings** (tab trên cùng)
3. Bên trái chọn **Secrets and variables** → **Actions**
4. Click **New repository secret** và thêm từng cái:

| Secret Name | Giá trị | Lấy ở đâu |
|-------------|---------|-----------|
| `GEMINI_API_KEY` | AIza... | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `GUMROAD_API_KEY` | gum_... | Gumroad Settings → Advanced → API |
| `PAYHIP_API_KEY` | ph_... | Payhip Settings → API |

> ⚠️ **Quan trọng**: Tên Secret phải CHÍNH XÁC như trong bảng (có phân biệt HOA/thường)

---

### Bước 2 — Tạo file sách

Mỗi quyển sách = 1 file `.yml` trong thư mục `books/`.

1. Vào thư mục `books/` trong repo
2. Click **Add file** → **Create new file**
3. Đặt tên: `ten-sach-cua-ban.yml`
4. Copy nội dung từ `example-book.yml` và sửa lại:

```yaml
title: "Tiêu đề sách của bạn"
author: "Tên tác giả"
niche: "Self-help"
languages:
  - en
  - vi
price_usd: 9.99

youtube_urls:
  - https://www.youtube.com/watch?v=LINK1
  - https://www.youtube.com/watch?v=LINK2
  # ... thêm 10-20 links
```

5. Click **Commit changes** (nút xanh)

---

### Bước 3 — Chạy pipeline

**Tự động theo lịch:**  
Pipeline chạy mỗi **Thứ Hai lúc 9PM** (giờ Houston) — không cần làm gì thêm.

**Chạy thủ công ngay:**
1. Vào tab **Actions** trong repo
2. Chọn **📚 Auto Book Builder** bên trái
3. Click **Run workflow** → **Run workflow** (nút xanh)
4. Chờ ~30-45 phút

---

### Bước 4 — Download file sách

Sau khi pipeline chạy xong:

1. Vào tab **Actions** → click vào lần chạy mới nhất
2. Cuộn xuống phần **Artifacts**
3. Click **books-XXX** để download ZIP chứa tất cả file DOCX

**Hoặc** vào tab **Releases** — file sẽ được đính kèm tự động.

---

## 💡 Pipeline hoạt động như thế nào?

```
YouTube URLs
    ↓
[1] Fetch transcripts (youtube-transcript-api)
    ↓
[2] Gemini synthesizes key insights → tạo outline 12 chương
    ↓
[3] Viết từng chương theo 3 đoạn nhỏ (~650 words/đoạn)
    ↙              ↘
  English         Tiếng Việt
  (~25,000 words) (~25,000 từ)
    ↓
[4] Export DOCX (KDP format: 6×9", Times New Roman 12pt)
    ↓
[5] Auto-publish → Gumroad + Payhip
    ↓
[6] Upload ke GitHub Releases để download
```

**Tại sao viết theo đoạn nhỏ?**  
Gemini có giới hạn ~2000 tokens/lần output. Script viết từng section 650 words × 3 sections = ~2000 words/chương × 12 chương = **~25,000 words tổng**.

---

## ❓ Troubleshooting

**Pipeline fail ở bước transcript?**  
→ Video đó bị tắt caption. Thay bằng video khác có auto-captions.

**Gemini bị rate limit?**  
→ Script tự retry với delay. Free tier: 15 requests/phút. Nếu có nhiều sách, nâng lên Gemini Pro.

**File DOCX không mở được?**  
→ Download lại từ Artifacts. Đôi khi file bị corrupt nếu Action bị cancel giữa chừng.

---

## 📊 Chi phí ước tính mỗi quyển sách

| Dịch vụ | Chi phí |
|---------|---------|
| GitHub Actions | **Miễn phí** (2,000 phút/tháng) |
| Gemini API (free tier) | **Miễn phí** (~60 API calls/sách) |
| YouTube Transcript API | **Miễn phí** |
| **Tổng** | **$0** |
