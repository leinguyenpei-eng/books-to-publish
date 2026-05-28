"""
build_single.py
Wrapper để GitHub Actions build từng sách riêng lẻ.
Đọc BOOK_FILE env var → load config → gọi build_book()
"""
import os
import sys
import yaml
from pathlib import Path

# Thêm scripts/ vào path để import được build_book
sys.path.insert(0, str(Path(__file__).parent))
from build_book import build_book, log

def main():
    book_file = os.environ.get("BOOK_FILE", "")
    
    if not book_file:
        # Nếu không có BOOK_FILE, chạy tất cả (fallback)
        import glob
        files = sorted(glob.glob("books/*.yml"))
        if not files:
            log("❌ No .yml files in books/")
            sys.exit(1)
        log(f"No BOOK_FILE set — building all {len(files)} books")
        for f in files:
            config = yaml.safe_load(open(f, encoding="utf-8"))
            build_book(config)
        return

    # Build sách cụ thể
    book_path = Path(book_file)
    if not book_path.exists():
        log(f"❌ File not found: {book_file}")
        sys.exit(1)

    log(f"📖 Loading: {book_file}")
    config = yaml.safe_load(open(book_path, encoding="utf-8"))
    build_book(config)

if __name__ == "__main__":
    main()
