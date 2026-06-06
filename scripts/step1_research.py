"""
step1_research.py — Research & Outline
═══════════════════════════════════════
Source: tinh hoa từ book-automation/01_generate_ideas.py + build_book.py outline logic
- Đọc transcript từ NotebookLM (bạn paste thủ công 1 lần)
- Gemini 2.0 Flash tạo outline 12 chương chi tiết
- Output ra output/outline.json + output/title.txt
- Không bao giờ timeout (chạy dưới 30s)
"""
import json, os, re, sys, requests, yaml, glob
from pathlib import Path

GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "")
TOPIC       = os.environ.get("TOPIC", "")
CATEGORY    = os.environ.get("CATEGORY", "self-help")
AUTHOR      = os.environ.get("AUTHOR_NAME", "Anonymous")

OUT_DIR = Path("output")
OUT_DIR.mkdir(exist_ok=True)

GEMINI_MODELS = [
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
]

def call_gemini(prompt: str, retries: int = 3) -> str:
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    for attempt in range(retries):
        model = GEMINI_MODELS[min(attempt, len(GEMINI_MODELS)-1)]
        try:
            import time
            r = requests.post(
                f"{model}?key={GEMINI_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.7, "maxOutputTokens": 3000}},
                timeout=60
            )
            if r.status_code == 429:
                wait = [60, 120, 180][min(attempt, 2)]
                print(f"  ⚠ Gemini 429 rate limit — waiting {wait}s then retrying with next model...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            import time
            wait = 20 * (attempt + 1)
            print(f"  ⚠ Gemini attempt {attempt+1}: {e} — retry {wait}s")
            time.sleep(wait)
    raise RuntimeError("Gemini failed after all retries")

def load_transcript() -> str:
    """Load transcript from NotebookLM paste"""
    paths = ["output/transcript.txt", "books/transcript.txt"]
    # Also check book-specific slug folder
    if TOPIC:
        slug = re.sub(r"[^\w]", "-", TOPIC.lower())[:30]
        paths.append(f"books/{slug}/transcript.txt")
    for p in paths:
        if Path(p).exists():
            text = Path(p).read_text(encoding="utf-8").strip()
            if len(text.split()) > 50:
                print(f"✓ Transcript loaded from {p}: {len(text.split()):,} words")
                return text
    # No transcript — use topic only
    print("⚠ No transcript.txt found — generating outline from topic only")
    return ""

def build_outline(transcript: str) -> dict:
    topic_line = f"Topic: {TOPIC}" if TOPIC else ""
    transcript_section = f"\nTRANSCRIPT CONTENT:\n{transcript[:12000]}" if transcript else ""

    prompt = f"""You are an elite Non-fiction Book Author specializing in Amazon KDP bestsellers.
Your style blends the sharp, actionable tone of Codie Sanchez with Andrew Huberman's structured insights.

{topic_line}
Book category: {CATEGORY}
Target audience: busy professionals who want actionable insights

{transcript_section}

Create a complete 12-chapter book outline. Return ONLY valid JSON, no markdown, no explanation:
{{
  "final_title": "compelling book title (max 8 words)",
  "subtitle": "specific subtitle (max 12 words)",
  "description": "150-word Amazon KDP book description",
  "cover_theme": "green|lavender|peach|blue|dark|pink",
  "cover_art_prompt": "detailed AI image prompt — describe colors, mood, objects, art style. NO text NO words NO letters",
  "etsy_tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10","tag11","tag12","tag13"],
  "keywords_kdp": ["kw1","kw2","kw3","kw4","kw5","kw6","kw7"],
  "chapters": [
    {{
      "number": 1,
      "title": "specific chapter title",
      "premise": "2-sentence chapter premise",
      "key_points": ["actionable point 1", "actionable point 2", "actionable point 3", "actionable point 4"],
      "stories_or_examples": ["specific case study or story to feature"],
      "data_or_quotes": ["specific stat, finding, or insight"],
      "hook": "opening hook sentence"
    }}
  ]
}}

Exactly 12 chapters. Each title must be specific and compelling, not generic."""

    raw = call_gemini(prompt)
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            return json.loads(match.group())
        raise RuntimeError(f"Cannot parse Gemini outline response: {raw[:300]}")

# ── Main ──────────────────────────────────────────────────────────────────────
transcript = load_transcript()
print(f"🧠 Building 12-chapter outline with Gemini...")
outline = build_outline(transcript)

# Enrich with metadata
outline["author"]   = AUTHOR
outline["category"] = CATEGORY
outline["topic"]    = TOPIC
outline["pricing"]  = {
    "gumroad": {"price": 9.99},
    "payhip":  {"price": 9.99},
    "etsy":    {"price": 6.99},
    "kdp":     {"price": 9.99}
}

# Save transcript alongside outline for chapter writing jobs
if transcript:
    (OUT_DIR / "transcript.txt").write_text(transcript, encoding="utf-8")

(OUT_DIR / "outline.json").write_text(json.dumps(outline, indent=2, ensure_ascii=False), encoding="utf-8")
(OUT_DIR / "title.txt").write_text(outline["final_title"], encoding="utf-8")
(OUT_DIR / "progress.json").write_text(json.dumps({"chapters_done": [], "total": 12}), encoding="utf-8")

print(f"✅ Outline complete!")
print(f"   Title: {outline['final_title']}")
print(f"   Subtitle: {outline['subtitle']}")
print(f"   Chapters: {len(outline['chapters'])}")

# Output for GitHub Actions
book_id = re.sub(r"[^\w]", "_", outline["final_title"])[:30]
print(f"::set-output name=book_id::{book_id}")
print(f"::set-output name=chapters_count::{len(outline['chapters'])}")
