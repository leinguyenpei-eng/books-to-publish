"""
telegram_bot.py — Interactive Book Pipeline Bot
────────────────────────────────────────────────
Flow:
  Bot hỏi → User chọn:
    A) Gửi topic text → Gemini tìm YouTube URLs tự động
    B) Dán YouTube URLs → dùng links đó luôn

  → Gemini tạo 3 ý tưởng sách
  → User chọn 1 / 2 / 3 / cả 3
  → Fetch transcripts trên Oracle Cloud
  → Push .yml lên GitHub
  → GitHub Actions build (~35 phút)
  → Bot báo xong → hỏi viết tiếp không

Chạy: python telegram_bot.py
Cần:  pip install "python-telegram-bot[job-queue]" requests youtube-transcript-api yt-dlp
"""

import os, re, json, time, base64, logging, requests
from pathlib import Path
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# ── youtube transcript ────────────────────────────────────────────────────────
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YT_API_AVAILABLE = True
except ImportError:
    YT_API_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY     = os.environ.get("GEMINI_API_KEY", "")
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USERNAME    = os.environ.get("GITHUB_USERNAME", "")
GITHUB_REPO        = os.environ.get("GITHUB_REPO", "my-books")
AUTHOR_NAME        = os.environ.get("AUTHOR_NAME", "Alex Morgan")
ALLOWED_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")

GEMINI_URL  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
GITHUB_API  = "https://api.github.com"
STATE_FILE  = Path(__file__).parent / "bot_state.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── State persistence ─────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

def get_state(chat_id: str) -> dict:
    state = load_state()
    if chat_id not in state:
        state[chat_id] = {
            "mode": None,           # "topic" | "youtube"
            "pending_books": [],
            "current_book": None,
            "queue": [],
            "youtube_urls": []      # URLs user đã dán vào
        }
        save_state(state)
    return state[chat_id]

def update_state(chat_id: str, data: dict):
    state = load_state()
    state.setdefault(chat_id, {}).update(data)
    save_state(state)


# ── Gemini helper ─────────────────────────────────────────────────────────────
def call_gemini(prompt: str, retries=4) -> str:
    MODELS = [
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-8b:generateContent",
    ]
    for attempt in range(retries):
        model = MODELS[min(attempt, len(MODELS)-1)]
        try:
            r = requests.post(
                f"{model}?key={GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.8, "maxOutputTokens": 2048}},
                timeout=60)
            if r.status_code == 429:
                wait = [60, 90, 120, 180][min(attempt, 3)]
                log.warning(f"Gemini 429 — waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            wait = 30 * (attempt + 1)
            log.warning(f"Gemini attempt {attempt+1}: {e} — retry {wait}s")
            time.sleep(wait)
    raise RuntimeError("Gemini failed after retries")


# ── YouTube helpers ───────────────────────────────────────────────────────────
def extract_video_id(url: str) -> str:
    patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return ""

def is_youtube_url(text: str) -> bool:
    return bool(re.search(r"(youtube\.com|youtu\.be)", text))

def extract_all_youtube_urls(text: str) -> list:
    """Tìm tất cả YouTube URLs trong text."""
    pattern = r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})[^\s]*"
    matches = re.findall(r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)[^\s]+", text)
    return list(set(matches))

def fetch_transcript_oracle(url: str) -> str:
    """
    Fetch YouTube transcript trên Oracle Cloud.
    Oracle IP không bị YouTube block như GitHub Actions.
    """
    vid_id = extract_video_id(url)
    if not vid_id:
        return ""

    # Method 1: youtube-transcript-api
    if YT_API_AVAILABLE:
        try:
            parts = YouTubeTranscriptApi.get_transcript(vid_id, languages=["en", "en-US", "en-GB"])
            text  = " ".join(p["text"] for p in parts)
            if len(text.split()) > 50:
                log.info(f"  ✓ Transcript API: {len(text.split())} words")
                return text
        except Exception as e:
            log.warning(f"  Transcript API failed: {e}")

    # Method 2: yt-dlp
    try:
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                ["yt-dlp", "--write-auto-sub", "--skip-download",
                 "--sub-format", "vtt", "--sub-lang", "en",
                 "--output", f"{tmp}/%(id)s", url],
                capture_output=True, text=True, timeout=30
            )
            vtt_files = list(Path(tmp).glob("*.vtt"))
            if vtt_files:
                raw = vtt_files[0].read_text(encoding="utf-8", errors="ignore")
                # Clean VTT format
                lines = []
                for line in raw.split("\n"):
                    if (not line.strip().startswith("WEBVTT") and
                        not re.match(r"^\d{2}:\d{2}", line) and
                        not re.match(r"^<\d{2}:", line) and
                        line.strip() and
                        not line.strip().isdigit()):
                        clean = re.sub(r"<[^>]+>", "", line).strip()
                        if clean:
                            lines.append(clean)
                text = " ".join(lines)
                if len(text.split()) > 50:
                    log.info(f"  ✓ yt-dlp: {len(text.split())} words")
                    return text
    except Exception as e:
        log.warning(f"  yt-dlp failed: {e}")

    return ""

def find_youtube_urls_for_topic(topic: str) -> list:
    """Dùng Gemini để suggest YouTube URLs phù hợp với topic."""
    prompt = f"""Find 6-8 real YouTube video URLs about this topic: "{topic}"

These should be educational videos from channels like:
- Codie Sanchez (business, investing)
- Andrew Huberman (health, performance)
- Ali Abdaal (productivity, study)
- Graham Stephan (finance)
- Mark Manson (self-help)
- Other credible educational channels

Return ONLY a JSON array of YouTube URLs, no explanation, no markdown:
["https://www.youtube.com/watch?v=VIDEO_ID1", "https://www.youtube.com/watch?v=VIDEO_ID2", ...]

Use real video IDs (11 characters). Topic: {topic}"""

    raw   = call_gemini(prompt)
    clean = re.sub(r"```json|```", "", raw).strip()
    try:
        urls = json.loads(clean)
        return [u for u in urls if is_youtube_url(u)][:8]
    except Exception:
        # Fallback: extract from text
        return extract_all_youtube_urls(raw)[:8]


# ── Book idea generation ──────────────────────────────────────────────────────
def generate_book_ideas(topic: str, youtube_urls: list = None) -> list:
    urls_context = ""
    if youtube_urls:
        urls_context = f"\nYouTube sources to base the book on:\n" + "\n".join(youtube_urls)

    prompt = f"""You are a KDP bestselling book expert.

Topic: {topic}{urls_context}

Create exactly 3 different book ideas for self-publishing on Amazon KDP, Gumroad, Etsy.
Each should target a DIFFERENT angle or audience.

Respond ONLY with valid JSON array — no markdown, no backticks:
[
  {{
    "title": "SEO-optimized title, 5-7 words",
    "subtitle": "Compelling subtitle, max 10 words",
    "niche": "Self-help",
    "description": "2 sentences describing the book and its value",
    "price_usd": 9.99,
    "youtube_urls": {json.dumps(youtube_urls or [])}
  }}
]

Niche options: Self-help | Business | Finance | Health | Productivity | How-to
Make all 3 books distinct — different titles, angles, audiences."""

    raw   = call_gemini(prompt)
    clean = re.sub(r"```json|```", "", raw).strip()
    try:
        books = json.loads(clean)
        assert isinstance(books, list)
        return books[:3]
    except Exception:
        m = re.search(r"\[[\s\S]*\]", clean)
        if m:
            return json.loads(m.group())[:3]
        raise ValueError(f"Cannot parse book ideas: {raw[:200]}")


# ── GitHub helpers ────────────────────────────────────────────────────────────
def github_push_file(file_path: str, content: str, commit_msg: str) -> bool:
    url = f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}",
               "Accept": "application/vnd.github.v3+json"}
    sha = None
    check = requests.get(url, headers=headers, timeout=10)
    if check.status_code == 200:
        sha = check.json().get("sha")

    payload = {
        "message": commit_msg,
        "content": base64.b64encode(content.encode()).decode(),
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload, timeout=30)
    return r.status_code in (200, 201)

def github_get_run_status(run_id: int) -> tuple:
    url = f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/actions/runs/{run_id}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}",
               "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        d = r.json()
        return d.get("status", ""), d.get("conclusion", ""), d.get("html_url", "")
    return "", "", ""

def make_slug(title: str) -> str:
    date_str = datetime.now().strftime("%Y%m%d-%H%M")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:35]
    return f"{date_str}-{slug}"

def build_yml(book: dict, author: str, transcripts: dict = None) -> str:
    urls      = book.get("youtube_urls", [])
    url_lines = "\n".join(f"  - {u}" for u in urls)
    title     = book.get("title", "Untitled").replace('"', "'")
    sub       = book.get("subtitle", "").replace('"', "'")
    desc      = book.get("description", "").replace('"', "'")

    # Embed transcript nếu đã fetch được (tránh GitHub Actions bị block)
    transcript_section = ""
    if transcripts:
        combined = "\n\n".join(
            f"=== {url} ===\n{text}"
            for url, text in transcripts.items()
            if text
        )
        if combined:
            # Encode để tránh ký tự đặc biệt trong YAML
            encoded = base64.b64encode(combined.encode()).decode()
            transcript_section = f"\n# Transcripts pre-fetched on Oracle Cloud\ntranscripts_b64: |\n  {encoded}\n"

    return f'''title: "{title}"
subtitle: "{sub}"
author: "{author}"
niche: "{book.get('niche', 'Self-help')}"
languages:
  - en
  - vi
price_usd: {book.get('price_usd', 9.99)}
description: "{desc}"

youtube_urls:
{url_lines}
{transcript_section}'''


# ── Telegram UI ───────────────────────────────────────────────────────────────
async def ask_what_to_write(chat_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Hỏi user hôm nay muốn viết sách gì."""
    keyboard = [[
        InlineKeyboardButton("📝 Gửi topic", callback_data="mode_topic"),
        InlineKeyboardButton("🎥 Dán link YouTube", callback_data="mode_youtube"),
    ]]
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "📚 *Hôm nay muốn viết sách gì?*\n\n"
            "Chọn cách bắt đầu:"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ── Handlers ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_what_to_write(str(update.effective_chat.id), context)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Book Pipeline Bot*\n\n"
        "*2 cách dùng:*\n"
        "📝 Gửi topic → bot tìm YouTube tự động\n"
        "🎥 Dán link YouTube → dùng links đó luôn\n\n"
        "*Lệnh:*\n"
        "/start — Bắt đầu viết sách mới\n"
        "/status — Xem tiến độ build\n"
        "/queue — Xem danh sách sách đang chờ\n\n"
        "*Ví dụ topic:*\n"
        "`habits for software developers`\n"
        "`personal finance for millennials`\n"
        "`anxiety management teens`",
        parse_mode="Markdown"
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/actions/runs"
    headers = {"Authorization": f"token {GITHUB_TOKEN}",
               "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers, params={"per_page": 1}, timeout=10)
    if r.status_code != 200:
        await update.message.reply_text("❌ Không lấy được status từ GitHub.")
        return
    runs = r.json().get("workflow_runs", [])
    if not runs:
        await update.message.reply_text("Chưa có build nào.")
        return
    run        = runs[0]
    status     = run.get("status", "")
    conclusion = run.get("conclusion", "")
    name       = run.get("name", "")
    link       = run.get("html_url", "")
    created    = run.get("created_at", "")[:16].replace("T", " ")
    emoji      = {"completed": "✅", "in_progress": "⏳", "queued": "🔜"}.get(status, "❓")
    con_emoji  = {"success": "✅", "failure": "❌", "cancelled": "⚠️"}.get(conclusion, "")
    await update.message.reply_text(
        f"{emoji} *{name}*\nStatus: `{status}` {con_emoji}\n"
        f"Started: {created}\n[Xem GitHub]({link})",
        parse_mode="Markdown", disable_web_page_preview=True
    )

async def cmd_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    s       = get_state(chat_id)
    queue   = s.get("queue", [])
    current = s.get("current_book")
    if not current and not queue:
        await update.message.reply_text("📭 Queue trống. Dùng /start để viết sách mới!")
        return
    lines = ["📋 *Queue sách:*\n"]
    if current:
        lines.append(f"⏳ *Đang build:* {current.get('title','?')}")
    for i, b in enumerate(queue, 1):
        lines.append(f"{i}. {b.get('title','?')}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = str(query.message.chat_id)
    data    = query.data
    await query.answer()

    # ── Mode selection ─────────────────────────────────────────────────────────
    if data == "mode_topic":
        update_state(chat_id, {"mode": "topic", "youtube_urls": []})
        await query.edit_message_text(
            "📝 *Gửi topic bạn muốn viết sách về:*\n\n"
            "Ví dụ:\n"
            "`habits for software developers`\n"
            "`personal finance for millennials`\n"
            "`morning routine for entrepreneurs`\n"
            "`anxiety management for teens`",
            parse_mode="Markdown"
        )
        return

    if data == "mode_youtube":
        update_state(chat_id, {"mode": "youtube", "youtube_urls": []})
        await query.edit_message_text(
            "🎥 *Dán link YouTube bạn muốn dùng làm nguồn:*\n\n"
            "Có thể dán nhiều links cùng lúc, ví dụ:\n"
            "`https://youtube.com/watch?v=abc123`\n"
            "`https://youtube.com/watch?v=def456`\n\n"
            "Dán xong bấm *Dùng các links này* để tiếp tục.\n\n"
            "_Mình sẽ fetch transcript từ các video này làm nguồn nghiên cứu._",
            parse_mode="Markdown"
        )
        return

    # ── Confirm YouTube URLs ────────────────────────────────────────────────────
    if data == "confirm_youtube":
        s    = get_state(chat_id)
        urls = s.get("youtube_urls", [])
        if not urls:
            await query.edit_message_text("❌ Chưa có link nào. Dán link YouTube vào đây:")
            return
        await query.edit_message_text(
            f"✅ *{len(urls)} links đã xác nhận*\n\n"
            "Bây giờ gửi *topic* cho cuốn sách:\n"
            "_Ví dụ: 'habits and productivity', 'sleep optimization', ..._",
            parse_mode="Markdown"
        )
        update_state(chat_id, {"mode": "topic_with_youtube"})
        return

    if data == "add_more_youtube":
        await query.edit_message_text(
            "🎥 Dán thêm links YouTube:",
            parse_mode="Markdown"
        )
        return

    # ── Book selection ──────────────────────────────────────────────────────────
    if data.startswith("pick_") and data != "pick_all":
        idx  = int(data.split("_")[1])
        s    = get_state(chat_id)
        books = s.get("pending_books", [])
        if idx >= len(books):
            await query.edit_message_text("❌ Không tìm thấy sách.")
            return
        await _push_book(chat_id, books[idx], s, context, query.message)
        return

    if data == "pick_all":
        s     = get_state(chat_id)
        books = s.get("pending_books", [])
        if not books:
            await query.edit_message_text("❌ Không có sách nào.")
            return
        update_state(chat_id, {"queue": list(books[1:])})
        await _push_book(chat_id, books[0], s, context, query.message)
        return

    if data == "regenerate":
        await query.edit_message_text(
            "🔄 Gửi lại topic để tạo 3 ý tưởng mới!",
            parse_mode="Markdown"
        )
        update_state(chat_id, {"mode": get_state(chat_id).get("mode", "topic")})
        return

    # ── Next book in queue ─────────────────────────────────────────────────────
    if data == "next_yes":
        s     = get_state(chat_id)
        queue = s.get("queue", [])
        if queue:
            next_book = queue.pop(0)
            update_state(chat_id, {"queue": queue})
            await _push_book(chat_id, next_book, s, context, query.message)
        else:
            await query.edit_message_text(
                "🎉 *Tất cả sách đã build xong!*\n\nDùng /start để viết thêm.",
                parse_mode="Markdown"
            )
        return

    if data == "next_no":
        await query.edit_message_text(
            "👍 Ok! Dùng /start bất cứ lúc nào để tiếp tục.",
            parse_mode="Markdown"
        )
        update_state(chat_id, {"current_book": None})
        return


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý text message từ user."""
    chat_id = str(update.effective_chat.id)
    text    = update.message.text.strip()

    # Security
    if ALLOWED_CHAT_ID and chat_id != str(ALLOWED_CHAT_ID):
        return

    s    = get_state(chat_id)
    mode = s.get("mode")

    # ── Mode: nhận YouTube URLs ────────────────────────────────────────────────
    if mode == "youtube":
        urls = extract_all_youtube_urls(text)
        if not urls:
            await update.message.reply_text(
                "⚠️ Không tìm thấy link YouTube nào.\n"
                "Dán link dạng: `https://youtube.com/watch?v=...`",
                parse_mode="Markdown"
            )
            return

        existing = s.get("youtube_urls", [])
        all_urls = list(set(existing + urls))
        update_state(chat_id, {"youtube_urls": all_urls})

        lines = [f"🎥 *{len(all_urls)} YouTube links:*\n"]
        for i, u in enumerate(all_urls, 1):
            vid_id = extract_video_id(u)
            lines.append(f"{i}. `{vid_id}` — {u[:50]}...")

        keyboard = [[
            InlineKeyboardButton("✅ Dùng các links này", callback_data="confirm_youtube"),
            InlineKeyboardButton("➕ Thêm links khác", callback_data="add_more_youtube"),
        ]]
        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ── Mode: nhận topic (có hoặc không có YouTube URLs) ───────────────────────
    if mode in ("topic", "topic_with_youtube", None):
        topic     = text
        yt_urls   = s.get("youtube_urls", [])

        msg = await update.message.reply_text(
            f"⏳ *Đang xử lý: {topic}*\n\n"
            f"{'🎥 Dùng ' + str(len(yt_urls)) + ' links YouTube của bạn' if yt_urls else '🔍 Tìm YouTube URLs phù hợp...'}\n"
            f"📚 Tạo 3 ý tưởng sách...",
            parse_mode="Markdown"
        )

        try:
            # Tìm YouTube URLs nếu user chưa cung cấp
            if not yt_urls:
                await msg.edit_text(
                    f"🔍 *Đang tìm YouTube URLs cho: {topic}*\n_(~15 giây...)_",
                    parse_mode="Markdown"
                )
                yt_urls = find_youtube_urls_for_topic(topic)
                log.info(f"Found {len(yt_urls)} YouTube URLs for topic: {topic}")

            await msg.edit_text(
                f"📚 *Đang tạo 3 ý tưởng sách...*\n"
                f"🎥 {len(yt_urls)} YouTube sources",
                parse_mode="Markdown"
            )

            books = generate_book_ideas(topic, yt_urls)

        except Exception as e:
            await msg.edit_text(f"❌ Lỗi: `{str(e)[:200]}`", parse_mode="Markdown")
            return

        # Lưu state
        update_state(chat_id, {
            "pending_books": books,
            "youtube_urls":  yt_urls,
            "mode":          None
        })

        # Show 3 lựa chọn
        lines = [f"📚 *3 ý tưởng sách cho: _{topic}_*\n"]
        for i, b in enumerate(books, 1):
            lines.append(
                f"*{i}. {b['title']}*\n"
                f"   _{b.get('subtitle', '')}_\n"
                f"   📁 {b.get('niche','')} · 💰 ${b.get('price_usd',9.99)}\n"
                f"   {b.get('description','')}\n"
            )
        lines.append("👇 *Chọn sách muốn viết:*")

        keyboard = [
            [
                InlineKeyboardButton("📗 Sách 1", callback_data="pick_0"),
                InlineKeyboardButton("📘 Sách 2", callback_data="pick_1"),
                InlineKeyboardButton("📕 Sách 3", callback_data="pick_2"),
            ],
            [InlineKeyboardButton("✅ Viết cả 3 (lần lượt)", callback_data="pick_all")],
            [InlineKeyboardButton("🔄 Tạo 3 ý tưởng khác", callback_data="regenerate")],
        ]

        await msg.edit_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Fallback — không biết mode
    await ask_what_to_write(chat_id, context)


# ── Push book to GitHub ────────────────────────────────────────────────────────
async def _push_book(chat_id: str, book: dict, state: dict,
                      context: ContextTypes.DEFAULT_TYPE, edit_msg=None):
    title    = book.get("title", "Untitled")
    slug     = make_slug(title)
    yt_urls  = book.get("youtube_urls", [])

    # Fetch transcripts trên Oracle Cloud (IP không bị block)
    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"📥 *Đang fetch {len(yt_urls)} transcripts từ YouTube...*\n_(Oracle Cloud fetch, không bị block)_",
        parse_mode="Markdown"
    )

    transcripts = {}
    success_count = 0
    for i, url in enumerate(yt_urls, 1):
        await status_msg.edit_text(
            f"📥 *Fetching transcript {i}/{len(yt_urls)}...*\n`{url[:60]}`",
            parse_mode="Markdown"
        )
        text = fetch_transcript_oracle(url)
        if text:
            transcripts[url] = text
            success_count += 1
        time.sleep(1)

    await status_msg.edit_text(
        f"{'✅' if success_count > 0 else '⚠️'} *Fetch xong: {success_count}/{len(yt_urls)} transcripts*\n"
        f"{'📝 Transcripts embedded vào .yml → GitHub Actions sẽ dùng luôn' if success_count > 0 else '🤖 Không lấy được transcript → Claude sẽ tự research'}",
        parse_mode="Markdown"
    )

    # Build YML với transcripts đã embed
    yml      = build_yml(book, AUTHOR_NAME, transcripts if transcripts else None)
    yml_path = f"books/{slug}.yml"

    # Push lên GitHub
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🚀 *Bắt đầu viết sách:*\n\n"
            f"📚 *{title}*\n"
            f"_{book.get('subtitle', '')}_\n\n"
            f"🎥 {success_count} transcripts đính kèm\n"
            f"⏳ GitHub Actions đang chạy (~35 phút)\n"
            f"Mình sẽ báo ngay khi xong!\n\n"
            f"[Xem tiến độ](https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}/actions)"
        ),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

    ok = github_push_file(yml_path, yml, f"📚 {title[:60]}")
    if not ok:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Push GitHub thất bại. Kiểm tra GITHUB_TOKEN."
        )
        return

    # Track run sau 2 phút
    run_data = {"chat_id": chat_id, "title": title, "attempt": 0,
                "book": book, "run_id": None}
    update_state(chat_id, {
        "current_book": {"title": title, "slug": slug, "started": datetime.now().isoformat()}
    })

    context.job_queue.run_once(
        _track_run, when=120,
        data=run_data, name=f"track_{chat_id}_{slug}"
    )


async def _track_run(context: ContextTypes.DEFAULT_TYPE):
    """Poll GitHub Actions để detect khi build xong."""
    d       = context.job.data
    chat_id = d["chat_id"]
    title   = d["title"]
    attempt = d["attempt"]
    run_id  = d.get("run_id")

    if attempt > 25:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Build *{title}* đã chạy >75 phút.\nKiểm tra thủ công tại GitHub Actions.",
            parse_mode="Markdown"
        )
        return

    # Lấy run_id lần đầu
    if not run_id:
        url = f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/actions/runs"
        headers = {"Authorization": f"token {GITHUB_TOKEN}",
                   "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers, params={"per_page": 3}, timeout=10)
        if r.status_code == 200:
            runs = r.json().get("workflow_runs", [])
            for run in runs:
                if run.get("status") in ("in_progress", "queued"):
                    run_id = run["id"]
                    d["run_id"] = run_id
                    break

    # Check status
    if run_id:
        status, conclusion, link = github_get_run_status(run_id)
    else:
        status, conclusion, link = "", "", ""

    if status == "completed":
        s     = load_state().get(chat_id, {})
        queue = s.get("queue", [])
        ok    = conclusion == "success"

        msg = (
            f"{'✅' if ok else '❌'} *{'Xong' if ok else 'Lỗi'}: {title}*\n\n"
        )
        if ok:
            msg += (
                "📁 Files trong GitHub Releases\n"
                "🛒 Đã publish lên Gumroad, Payhip, Etsy\n"
            )
        else:
            msg += f"Conclusion: `{conclusion}`\n[Xem lỗi]({link})\n"

        if queue:
            next_b = queue[0]
            msg   += f"\n📚 *Sách tiếp theo:*\n_{next_b.get('title','?')}_\n\nViết ngay không?"
            kb     = [[
                InlineKeyboardButton("✅ Viết tiếp", callback_data="next_yes"),
                InlineKeyboardButton("⏸ Để sau", callback_data="next_no"),
            ]]
        else:
            msg += "\n\nDùng /start để viết thêm sách! 📚"
            kb   = None

        await context.bot.send_message(
            chat_id=chat_id, text=msg, parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(kb) if kb else None
        )
        update_state(chat_id, {"current_book": None})
        return

    # Đang chạy → poll tiếp
    context.job_queue.run_once(
        _track_run, when=180,
        data={**d, "attempt": attempt + 1, "run_id": run_id},
        name=f"track_{chat_id}_{attempt+1}"
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    missing = [k for k, v in {
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "GEMINI_API_KEY":     GEMINI_API_KEY,
        "GITHUB_TOKEN":       GITHUB_TOKEN,
        "GITHUB_USERNAME":    GITHUB_USERNAME,
    }.items() if not v]

    if missing:
        print(f"❌ Thiếu env vars: {', '.join(missing)}")
        print("   Copy .env.example → .env và điền vào")
        return

    print(f"🤖 Book Pipeline Bot đang chạy...")
    print(f"   Repo: {GITHUB_USERNAME}/{GITHUB_REPO}")
    print(f"   Nhắn bot Telegram để bắt đầu!")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("queue",  cmd_queue))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
