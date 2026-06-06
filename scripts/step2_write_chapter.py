"""
step2_write_chapter.py — Write ONE chapter (called per job in matrix)
═══════════════════════════════════════════════════════════════════════
Source: tinh hoa từ pipeline-merged (3-section writing) + book-final (system prompts)
         + book-automation (email per chapter) + generate_book_v2.yml (job matrix)
- Đọc outline.json từ step 1
- Claude viết chương thành 3 sections (open/middle/close) — tránh timeout
- Mỗi section ~700 words → total ~2,100-2,500 words/chapter
- Gửi email ngay sau khi xong
- Save chapter_XX.txt vào output/
"""
import json, os, re, sys, time, smtplib, requests
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CLAUDE_KEY     = os.environ.get("ANTHROPIC_API_KEY", "")
CHAPTER_NUMBER = int(os.environ.get("CHAPTER_NUMBER", "1"))
GMAIL_USER     = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASS = os.environ.get("GMAIL_APP_PASSWORD", "")
GMAIL_TO       = os.environ.get("GMAIL_TO", "") or GMAIL_USER

CLAUDE_MODEL = "claude-sonnet-4-6"
OUT_DIR      = Path("output")

# ── Load outline ──────────────────────────────────────────────────────────────
outline_path = OUT_DIR / "outline.json"
if not outline_path.exists():
    print("❌ output/outline.json not found — run step1 first")
    sys.exit(1)

outline  = json.loads(outline_path.read_text(encoding="utf-8"))
chapters = outline["chapters"]

# Find this chapter
ch = next((c for c in chapters if c["number"] == CHAPTER_NUMBER), None)
if not ch:
    print(f"❌ Chapter {CHAPTER_NUMBER} not found in outline")
    sys.exit(1)

book_title = outline["final_title"]
niche      = outline.get("category", "self-help")

# Load transcript for context
transcript = ""
if (OUT_DIR / "transcript.txt").exists():
    transcript = (OUT_DIR / "transcript.txt").read_text(encoding="utf-8")[:8000]

# ── Claude ────────────────────────────────────────────────────────────────────
CHAPTER_SYSTEM = """You are ghostwriting a premium Non-fiction book for Amazon KDP.
Your goal: write prose that feels 100% human — a real expert who has lived through this material.

═══ VOICE & RHYTHM ═══
- Vary sentence length deliberately: short punchy sentences. Then a longer one that builds a thought, adds texture, and earns its length before landing. Then short again.
- Add 1-2 natural imperfections per section: a rhetorical question the reader is already thinking, a brief digression that circles back, a moment of honest uncertainty ("The data here is murkier than you'd expect.")
- Write like Codie Sanchez at her most direct, or Malcolm Gladwell at his most curious — sharp, grounded, occasionally surprising.
- Use specific anecdotes, named places, real numbers. Not "a study found" but "a 2019 Stanford study of 400 middle managers found."
- First-person voice is allowed sparingly: "Here's what that actually means in practice." "I've seen this go wrong in three distinct ways."

═══ BANNED WORDS (AI fingerprints — never use these) ═══
Delve, Crucial, Leverage, Utilize, Synergy, Tapestry, Embark, Navigate/Navigating,
"It is important to note", "It's worth noting", "In today's fast-paced world",
"In conclusion", "Furthermore", "Moreover", "Overall", "In summary",
"This chapter will explore", "Let's dive into", "At the end of the day",
"Game-changer", "Paradigm shift", "Move the needle", "Cutting-edge", "Holistic"

═══ STRUCTURE RULES ═══
- Fluent, premium American English only
- Short paragraphs (3-5 sentences max)
- Use ## Subheadings naturally — not every 2 paragraphs, only when the topic genuinely shifts
- NO bullet lists — weave everything into flowing prose
- ZERO repetition — never restate the same point twice, even in different words
- Every argument MUST have a concrete example, story, or specific data point
- Start directly with content — no "Section X:" labels, no preamble, no "In this section we will..."
- NO summary paragraph at the end of sections — end mid-momentum, not with a bow"""

def call_claude(prompt: str, max_tokens: int = 1500, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": max_tokens,
                    "system": CHAPTER_SYSTEM,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=180
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"].strip()
        except Exception as e:
            wait = 30 * (attempt + 1)
            print(f"  ⚠ Claude attempt {attempt+1}: {e} — retry {wait}s")
            time.sleep(wait)
    raise RuntimeError("Claude failed after all retries")

# ── Write 3 sections ──────────────────────────────────────────────────────────
kp = "\n".join(f"- {p}" for p in ch.get("key_points", []))
st = "\n".join(f"- {s}" for s in ch.get("stories_or_examples", []))
da = "\n".join(f"- {d}" for d in ch.get("data_or_quotes", []))

# Get neighboring chapters for continuity
prev_title = chapters[CHAPTER_NUMBER-2]["title"] if CHAPTER_NUMBER > 1 else None
next_title = chapters[CHAPTER_NUMBER]["title"] if CHAPTER_NUMBER < len(chapters) else None
context = ""
if prev_title: context += f"Previous chapter: '{prev_title}'\n"
if next_title:  context += f"Next chapter: '{next_title}'\n"

AUTHOR = os.environ.get("AUTHOR_STYLE", "")
style_line = f"\nWrite in the style of: {AUTHOR}" if AUTHOR else \
             "\nWrite in the style of: Codie Sanchez (sharp, actionable, no fluff) crossed with Malcolm Gladwell (curious, story-driven, counterintuitive)"

base_prompt = f"""Book: "{book_title}" ({niche})
Chapter {CHAPTER_NUMBER}: {ch['title']}
Premise: {ch.get('premise', '')}
Hook: {ch.get('hook', '')}
{style_line}

Key points:
{kp}

Stories/Examples to weave in:
{st}

Data/Insights to reference:
{da}

{context}
{"SOURCE MATERIAL:" + chr(10) + transcript if transcript else ""}"""

print(f"✍ Writing Chapter {CHAPTER_NUMBER}: {ch['title']}")

# Section 1: Opening
print("  §1/3 Opening...")
s1 = call_claude(
    base_prompt + "\n\nWrite the OPENING of this chapter (target ~700 words). "
    "Start with the hook. Introduce the chapter premise compellingly. "
    "End mid-thought to flow naturally into the next section.",
    max_tokens=1200
)
print(f"    ✓ {len(s1.split())} words")
time.sleep(5)

# Section 2: Middle
print("  §2/3 Middle...")
s2 = call_claude(
    base_prompt + f"\n\nCONTINUE SEAMLESSLY from this opening:\n'...{s1[-400:]}'\n\n"
    "Write the MIDDLE of this chapter (target ~700 words). "
    "Deep dive into key points. Weave in stories and data. Build momentum. "
    "End naturally to flow into closing.",
    max_tokens=1200
)
print(f"    ✓ {len(s2.split())} words")
time.sleep(5)

# Section 3: Closing
print("  §3/3 Closing...")
s3 = call_claude(
    base_prompt + f"\n\nCONTINUE SEAMLESSLY from this section:\n'...{s2[-400:]}'\n\n"
    "Write the CLOSING of this chapter (target ~700 words). "
    "Synthesize the key ideas — but do NOT just summarize. "
    "Give 1 concrete action step. Bridge naturally to the next chapter topic. "
    "NO 'In conclusion' or summary paragraphs.",
    max_tokens=1200
)
print(f"    ✓ {len(s3.split())} words")

# ── Combine ───────────────────────────────────────────────────────────────────
full_chapter = f"{s1}\n\n{s2}\n\n{s3}"
word_count   = len(full_chapter.split())
print(f"  ✓ Chapter {CHAPTER_NUMBER} complete: {word_count:,} words")

# ── Save ──────────────────────────────────────────────────────────────────────
chapter_file = OUT_DIR / f"chapter_{CHAPTER_NUMBER:02d}.txt"
chapter_file.write_text(
    f"CHAPTER {CHAPTER_NUMBER}: {ch['title']}\n{'='*60}\n\n{full_chapter}",
    encoding="utf-8"
)

# Update progress
progress_file = OUT_DIR / "progress.json"
progress = json.loads(progress_file.read_text()) if progress_file.exists() else {"chapters_done": [], "total": 12}
if CHAPTER_NUMBER not in progress["chapters_done"]:
    progress["chapters_done"].append(CHAPTER_NUMBER)
progress_file.write_text(json.dumps(progress, indent=2))

# ── Email chapter ─────────────────────────────────────────────────────────────
def send_email(subject, body):
    if not GMAIL_USER or not GMAIL_APP_PASS:
        print("  ⚠ Gmail not configured — skipping email")
        return
    try:
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_USER
        msg["To"]      = GMAIL_TO or GMAIL_USER
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASS)
            s.send_message(msg)
        print(f"  ✉ Email sent: {subject[:60]}")
    except Exception as e:
        print(f"  ⚠ Email failed: {e}")

remaining = 12 - CHAPTER_NUMBER
send_email(
    subject=f"✍ [{book_title}] Chapter {CHAPTER_NUMBER}/12 done: {ch['title']}",
    body=(
        f"Chapter {CHAPTER_NUMBER} of 12 has been written!\n\n"
        f"Book: {book_title}\n"
        f"Chapter: {ch['title']}\n"
        f"Words: {word_count:,}\n"
        f"Remaining: {remaining} chapters\n\n"
        f"{'='*60}\n\n"
        f"{full_chapter}"
    )
)

print(f"✅ Chapter {CHAPTER_NUMBER} saved to {chapter_file}")
