"""
YouTube → Book Pipeline  (Full version)
────────────────────────────────────────
Step 1  Fetch YouTube transcripts
Step 2  Gemini synthesizes outline
Step 3  Claude (OpenRouter) writes chapters in chunks
Step 4  Export DOCX (KDP format)
Step 5  Generate book cover (Imagen + Pillow overlay)
Step 6  Publish → Gumroad + Payhip + Beacons + Fourthwall
Step 7  Generate Facebook marketing posts
Step 8  Generate TikTok/Instagram/LinkedIn/Twitter content
Step 9  Send email campaign to subscribers
"""

import os, re, time, json, yaml, glob
import requests
from pathlib import Path
from datetime import datetime
# Transcript fetching handled by transcript_fetcher.py
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ── Keys (set as GitHub Secrets) ──────────────────────────────────────────────
GEMINI_KEY     = os.environ.get("GEMINI_API_KEY", "")
CLAUDE_KEY     = os.environ.get("ANTHROPIC_API_KEY", "")
GUMROAD_KEY    = os.environ.get("GUMROAD_API_KEY", "")
PAYHIP_KEY     = os.environ.get("PAYHIP_API_KEY", "")
BEACONS_KEY    = os.environ.get("BEACONS_API_KEY", "")
FOURTHWALL_KEY = os.environ.get("FOURTHWALL_API_KEY", "")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"  # Best balance speed/quality

# Luôn tạo outputs/ ở root của repo, dù chạy từ đâu
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


# ── Logging ───────────────────────────────────────────────────────────────────
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── AI callers ────────────────────────────────────────────────────────────────
def call_gemini(prompt: str, retries=3) -> str:
    for attempt in range(retries):
        try:
            r = requests.post(
                f"{GEMINI_URL}?key={GEMINI_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}},
                timeout=60)
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            wait = 20 * (attempt + 1)
            log(f"  ⚠ Gemini attempt {attempt+1}: {e} — retry {wait}s")
            time.sleep(wait)
    raise RuntimeError("Gemini failed after retries")


def call_claude(prompt: str, retries=3) -> str:
    """Gọi Claude API trực tiếp — dùng cho toàn bộ writing tasks."""
    if not CLAUDE_KEY:
        raise RuntimeError("No ANTHROPIC_API_KEY")
    for attempt in range(retries):
        try:
            r = requests.post(
                CLAUDE_URL,
                headers={
                    "x-api-key": CLAUDE_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 2048,
                    "temperature": 0.85,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=90)
            r.raise_for_status()
            data = r.json()
            return data["content"][0]["text"].strip()
        except Exception as e:
            wait = 20 * (attempt + 1)
            log(f"  ⚠ Claude attempt {attempt+1}: {e} — retry {wait}s")
            time.sleep(wait)
    raise RuntimeError("Claude API failed after retries")


def call_ai(prompt: str, prefer: str = "claude") -> str:
    """
    Smart router với auto-fallback:
    prefer=claude  → Claude API trước, fallback Gemini
    prefer=gemini  → Gemini trước, fallback Claude
    """
    if prefer == "claude":
        try:
            return call_claude(prompt)
        except Exception as e:
            log(f"  ↩ Claude failed ({e}), falling back to Gemini...")
            return call_gemini(prompt)
    else:
        try:
            return call_gemini(prompt)
        except Exception as e:
            log(f"  ↩ Gemini failed ({e}), falling back to Claude...")
            return call_claude(prompt)


# ── YouTube transcripts ───────────────────────────────────────────────────────
def fetch_transcript(url: str) -> str:
    """Dùng transcript_fetcher.py — hỗ trợ yt-dlp, transcript-api, YouTube API"""
    from transcript_fetcher import fetch_transcript as _fetch
    return _fetch(url)


def gather_sources(urls: list) -> str:
    log(f"📥 Fetching {len(urls)} transcripts...")
    parts = []
    for i, url in enumerate(urls, 1):
        log(f"  [{i}/{len(urls)}] {url[:65]}")
        t = fetch_transcript(url)
        if t:
            parts.append(f"=== SOURCE {i} ===\n{t}")
        time.sleep(1)
    combined = "\n\n".join(parts)
    log(f"✓ Total: {len(combined.split())} words from {len(parts)} sources")
    return combined


# ── Step 2: Outline via Gemini (large context) ────────────────────────────────
def build_outline(raw: str, config: dict) -> dict:
    log("🧠 Building outline (Gemini)...")
    title = config.get("title", "Untitled")
    niche = config.get("niche", "Self-help")

    prompt = f"""Analyze these YouTube transcripts and create a book outline for "{title}" ({niche}).

TRANSCRIPTS:
{raw[:80000]}

Return ONLY valid JSON, no markdown backticks:
{{
  "core_thesis": "2-3 sentences",
  "target_reader": "1 sentence",
  "introduction_hook": "3-4 sentence compelling hook",
  "conclusion_message": "2-3 sentence final message",
  "chapters": [
    {{
      "number": 1,
      "title": "Chapter title",
      "premise": "2 sentences",
      "key_points": ["point 1","point 2","point 3","point 4"],
      "stories_or_examples": ["example from transcripts"],
      "data_or_quotes": ["stat or quote from sources"]
    }}
  ]
}}
Generate exactly 12 chapters. ONLY JSON, nothing else."""

    raw_out = call_gemini(prompt)
    raw_out = re.sub(r"^```json\s*", "", raw_out, flags=re.MULTILINE)
    raw_out = re.sub(r"```\s*$", "", raw_out, flags=re.MULTILINE).strip()
    try:
        outline = json.loads(raw_out)
        log(f"✓ Outline ready: {len(outline['chapters'])} chapters")
        return outline
    except Exception:
        log("⚠ JSON parse failed — using fallback outline")
        return {
            "core_thesis": title, "target_reader": "General readers",
            "introduction_hook": "Begin.", "conclusion_message": "End.",
            "chapters": [{"number": i, "title": f"Chapter {i}",
                          "premise": "Key ideas.", "key_points": ["P1","P2","P3"],
                          "stories_or_examples": [], "data_or_quotes": []}
                         for i in range(1, 13)]
        }


# ── Step 3: Write chapters in chunks (Claude preferred) ───────────────────────
def write_section(ch: dict, config: dict, lang: str, s_num: int, prev: str) -> str:
    li    = "Write in English." if lang == "en" else "Viết hoàn toàn bằng Tiếng Việt tự nhiên."
    title = config.get("title","Untitled")
    niche = config.get("niche","Self-help")
    kp    = "\n".join(f"- {p}" for p in ch.get("key_points", []))
    st    = "\n".join(f"- {s}" for s in ch.get("stories_or_examples", []))
    da    = "\n".join(f"- {d}" for d in ch.get("data_or_quotes", []))

    tasks = {
        1: "Write the OPENING: hook + introduce premise. End mid-thought naturally.",
        2: f"CONTINUE from: '{prev[-200:]}'\nWrite the MIDDLE: deep dive, weave in stories and data.",
        3: f"CONTINUE from: '{prev[-200:]}'\nWrite the CLOSING: wrap up key ideas, 1 action step, bridge to next chapter.",
    }

    prompt = f"""You are ghostwriting a {niche} book titled "{title}".
{li}

CHAPTER {ch['number']}: {ch['title']}
Premise: {ch.get('premise','')}
Key points:
{kp}
Stories/Examples:
{st}
Data/Quotes:
{da}

TASK: {tasks[s_num]}

KDP nonfiction style rules:
- Conversational but authoritative
- Short paragraphs (3-5 sentences max)
- Use ## Subheading where natural
- No bullet lists — weave into flowing prose
- ~600-700 words
- Start directly with content, no labels

Write now:"""

    return call_ai(prompt, prefer="claude")


def write_chapter(ch: dict, config: dict, lang: str, ctx: str) -> str:
    log(f"  ✍ Ch.{ch['number']}: {ch['title']}")
    full = ""
    for s in range(1, 4):
        sec = write_section(ch, config, lang, s, full)
        full += "\n\n" + sec
        log(f"    §{s}/3 — {len(sec.split())} words")
        time.sleep(3)
    log(f"  ✓ Chapter done: {len(full.split())} words")
    return full.strip()


def write_intro_conclusion(outline: dict, config: dict, lang: str) -> tuple:
    li    = "Write in English." if lang == "en" else "Viết hoàn toàn bằng Tiếng Việt tự nhiên."
    title = config.get("title","Untitled")
    niche = config.get("niche","Self-help")

    log("  Writing Introduction...")
    intro = call_ai(f"""Write a compelling Introduction for "{title}" ({niche} book).
{li}
Hook: {outline.get('introduction_hook','')}
Thesis: {outline.get('core_thesis','')}
Reader: {outline.get('target_reader','')}
Briefly preview all 12 chapters. 800-1000 words. KDP style. Start directly:""",
        prefer="claude")

    time.sleep(3)
    log("  Writing Conclusion...")
    conclusion = call_ai(f"""Write a powerful Conclusion for "{title}" ({niche} book).
{li}
Message: {outline.get('conclusion_message','')}
Thesis: {outline.get('core_thesis','')}
600-800 words. Inspiring + actionable. Start directly:""",
        prefer="claude")

    return intro, conclusion


# ── Step 4: DOCX export (KDP 6×9) ────────────────────────────────────────────
def build_docx(ms: dict, config: dict, lang: str) -> Path:
    title  = config.get("title","Untitled")
    author = config.get("author","Unknown Author")
    suffix = "EN" if lang == "en" else "VI"
    path   = OUTPUT_DIR / f"{title} ({suffix}).docx"

    doc = Document()
    sec = doc.sections[0]
    sec.page_width   = Inches(6)
    sec.page_height  = Inches(9)
    sec.left_margin  = sec.right_margin  = Inches(0.75)
    sec.top_margin   = sec.bottom_margin = Inches(0.75)

    sty = doc.styles["Normal"]
    sty.font.name = "Times New Roman"
    sty.font.size = Pt(12)
    sty.paragraph_format.line_spacing = Pt(18)
    sty.paragraph_format.space_after  = Pt(0)

    def heading(text, level=1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(text)
        r.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(20 if level == 1 else 14)
        p.paragraph_format.space_before = Pt(24)
        p.paragraph_format.space_after  = Pt(12)

    def body(text):
        parts = re.split(r"\n##\s+(.+?)(?:\n|$)", text)
        i = 0
        while i < len(parts):
            for para in parts[i].strip().split("\n\n"):
                para = para.strip()
                if para:
                    p = doc.add_paragraph()
                    p.paragraph_format.first_line_indent = Inches(0.3)
                    p.paragraph_format.space_after = Pt(6)
                    r = p.add_run(para)
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(12)
            i += 1
            if i < len(parts):
                heading(parts[i].strip(), level=2)
                i += 1

    # Title page
    doc.add_paragraph()
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = tp.add_run(title)
    tr.bold = True; tr.font.size = Pt(24); tr.font.name = "Times New Roman"
    doc.add_paragraph()
    ap = doc.add_paragraph()
    ap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ap.add_run(f"by {author}").font.size = Pt(14)
    doc.add_page_break()

    heading("Introduction"); body(ms["introduction"]); doc.add_page_break()
    for ch in ms["chapters"]:
        heading(f"Chapter {ch['number']}: {ch['title']}")
        body(ch["content"])
        doc.add_page_break()
    heading("Conclusion"); body(ms["conclusion"])

    doc.save(str(path))
    log(f"✓ DOCX saved: {path}")
    return path


# ── Step 5: Cover image ───────────────────────────────────────────────────────
def make_cover(config: dict) -> Path | None:
    try:
        from cover_generator import make_cover as _make
        return _make(config)
    except Exception as e:
        log(f"⚠ Cover skipped: {e}")
        return None


# ── Step 6: Publish to all platforms ─────────────────────────────────────────
def publish_gumroad(path: Path, config: dict, cover: Path = None) -> str:
    if not GUMROAD_KEY:
        log("⚠ No GUMROAD_API_KEY"); return ""
    title = config.get("title","Untitled")
    price = int(float(config.get("price_usd", 9.99)) * 100)
    log(f"📤 Gumroad: {title}")
    r = requests.post("https://api.gumroad.com/v2/products", data={
        "access_token": GUMROAD_KEY, "name": title, "price": price,
        "description": config.get("description",""), "published": "true"})
    data = r.json()
    if not data.get("success"):
        log(f"  ⚠ {data}"); return ""
    pid = data["product"]["id"]
    with open(path,"rb") as f:
        requests.put(f"https://api.gumroad.com/v2/products/{pid}/files",
                     data={"access_token": GUMROAD_KEY},
                     files={"file": (path.name, f)})
    if cover and cover.exists():
        with open(cover,"rb") as f:
            requests.put(f"https://api.gumroad.com/v2/products/{pid}/cover_image",
                         data={"access_token": GUMROAD_KEY},
                         files={"cover_image": (cover.name, f, "image/jpeg")})
    url = data["product"].get("short_url","")
    log(f"  ✓ Gumroad: {url}")
    return url


def publish_payhip(path: Path, config: dict, cover: Path = None) -> str:
    if not PAYHIP_KEY:
        log("⚠ No PAYHIP_API_KEY"); return ""
    log(f"📤 Payhip: {config.get('title')} — add Payhip API endpoint here")
    return ""


def publish_beacons(path: Path, config: dict) -> str:
    if not BEACONS_KEY:
        log("⚠ No BEACONS_API_KEY"); return ""
    log(f"📤 Beacons: {config.get('title')}")
    try:
        r = requests.post("https://api.beacons.ai/v1/products",
            headers={"Authorization": f"Bearer {BEACONS_KEY}",
                     "Content-Type": "application/json"},
            json={"title": config.get("title",""),
                  "description": config.get("description",""),
                  "price": float(config.get("price_usd", 9.99)),
                  "currency": "USD", "type": "digital_download"},
            timeout=30)
        data = r.json()
        if data.get("id"):
            log(f"  ✓ Beacons: {data.get('url','')}")
            return data.get("url","")
        log(f"  ⚠ Beacons: {data}")
    except Exception as e:
        log(f"  ⚠ Beacons error: {e}")
    return ""


def publish_fourthwall(path: Path, config: dict) -> str:
    if not FOURTHWALL_KEY:
        log("⚠ No FOURTHWALL_API_KEY"); return ""
    log(f"📤 Fourthwall: {config.get('title')}")
    try:
        r = requests.post("https://api.fourthwall.com/v1/products",
            headers={"Authorization": f"Bearer {FOURTHWALL_KEY}",
                     "Content-Type": "application/json"},
            json={"name": config.get("title",""),
                  "description": config.get("description",""),
                  "price_in_cents": int(float(config.get("price_usd",9.99)) * 100),
                  "product_type": "digital"},
            timeout=30)
        data = r.json()
        if data.get("id"):
            log(f"  ✓ Fourthwall: {data.get('url','')}")
            return data.get("url","")
        log(f"  ⚠ Fourthwall: {data}")
    except Exception as e:
        log(f"  ⚠ Fourthwall error: {e}")
    return ""


# ── Step 7: Facebook posts ────────────────────────────────────────────────────
def generate_fb_posts(config: dict, buy_links: dict, cover: Path = None):
    try:
        from social_publisher import run_social_publisher
        run_social_publisher(config, buy_links, cover)
    except Exception as e:
        log(f"⚠ Social posts skipped: {e}")


# ── Main orchestrator ─────────────────────────────────────────────────────────
def build_book(config: dict):
    title = config.get("title","Untitled")
    urls  = config.get("youtube_urls",[])
    langs = config.get("languages",["en","vi"])

    log(f"\n{'='*60}\n📚 {title}\n   {len(urls)} sources · {', '.join(langs)}\n{'='*60}\n")

    # 1. Transcripts
    raw = gather_sources(urls)
    if not raw:
        log("⚠ No transcripts fetched — generating from video titles/descriptions instead")
        # Fallback: dùng titles của YouTube videos làm input cho Gemini
        raw = "\n".join([
            f"=== SOURCE {i+1} ===\nVideo URL: {url}\nTopic: {config.get('title', 'Unknown')} — {config.get('niche', 'Self-help')}"
            for i, url in enumerate(urls)
        ])
        log(f"📝 Using {len(urls)} video references as fallback input")

    # 2. Outline (Gemini — best for large context JSON)
    outline = build_outline(raw, config)
    (OUTPUT_DIR / f"{title}_outline.json").write_text(
        json.dumps(outline, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3+4. Write + DOCX for each language
    en_docx = None
    for lang in langs:
        flag = "🇺🇸 EN" if lang == "en" else "🇻🇳 VI"
        log(f"\n{flag} manuscript...\n")

        ms = {"introduction": "", "conclusion": "", "chapters": []}
        ms["introduction"], ms["conclusion"] = write_intro_conclusion(outline, config, lang)

        ctx = f'Book: {title}\nThesis: {outline.get("core_thesis","")}\n'
        for ch in outline["chapters"]:
            content = write_chapter(ch, config, lang, ctx)
            ms["chapters"].append({"number": ch["number"],
                                   "title": ch["title"],
                                   "content": content})
            ctx += f'\nCh.{ch["number"]} ({ch["title"]}): {content[:200]}...'

        all_words = len((ms["introduction"] + ms["conclusion"] +
                         " ".join(c["content"] for c in ms["chapters"])).split())
        log(f"\n✓ {flag}: {all_words:,} words")

        docx = build_docx(ms, config, lang)
        if lang == "en":
            en_docx = docx

    # 5. Book cover
    cover = make_cover(config)

    # 6. Publish everywhere
    buy_links = {}
    if en_docx:
        buy_links["Gumroad"]    = publish_gumroad(en_docx, config, cover)
        buy_links["Payhip"]     = publish_payhip(en_docx, config, cover)
        buy_links["Beacons"]    = publish_beacons(en_docx, config)
        buy_links["Fourthwall"] = publish_fourthwall(en_docx, config)

    # 7. Facebook posts
    generate_fb_posts(config, buy_links, cover)

    # 8. TikTok + Instagram + LinkedIn + Twitter
    try:
        from multi_social import run_multi_social
        run_multi_social(config, buy_links, cover)
    except Exception as e:
        log(f"⚠ Multi-social skipped: {e}")

    # 9. Email campaign
    try:
        from email_marketing import run_email_campaign
        run_email_campaign(config, buy_links, cover)
    except Exception as e:
        log(f"⚠ Email campaign skipped: {e}")

    log(f"\n🎉 Done! All files in: {OUTPUT_DIR}/")
    for k, v in buy_links.items():
        if v:
            log(f"  🔗 {k}: {v}")


def main():
    files = sorted(glob.glob("books/*.yml"))
    if not files:
        log("❌ No .yml files in books/"); return
    log(f"Found {len(files)} book(s): {files}")
    for f in files:
        config = yaml.safe_load(open(f, encoding="utf-8"))
        build_book(config)


if __name__ == "__main__":
    main()
