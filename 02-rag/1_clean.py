"""Step 1: Clean raw text.

input : data/{raw|my_raw}_data.txt
output: outputs/cleaned.txt
"""
import argparse
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
OUT_DIR = HERE / "outputs"

NOISE_PATTERNS = [
    re.compile(r"^\s*\[?페이지\s*\d+\]?\s*$"),     # [페이지 1]
    re.compile(r"^\s*-\s*\d+\s*-\s*$"),             # - 12 -
    re.compile(r"^\s*-\s*끝\s*-\s*$"),              # - 끝 -
    re.compile(r"^={3,}\s*$"),                       # =====
    re.compile(r"^-{3,}\s*$"),                       # -----
]


def is_noise(line: str) -> bool:
    return any(p.match(line) for p in NOISE_PATTERNS)


def clean(text: str) -> str:
    kept = []
    for ln in text.splitlines():
        if is_noise(ln):
            continue
        kept.append(re.sub(r"[ \t]+", " ", ln).rstrip())

    collapsed = []
    prev_blank = False
    for ln in kept:
        blank = not ln.strip()
        if blank and prev_blank:
            continue
        collapsed.append(ln)
        prev_blank = blank
    return "\n".join(collapsed).strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["raw", "my"], default="raw",
                    help="raw=data/raw_data.txt, my=data/my_raw_data.txt")
    args = ap.parse_args()

    src = DATA_DIR / ("raw_data.txt" if args.source == "raw" else "my_raw_data.txt")
    if not src.exists():
        raise SystemExit(f"입력 파일이 없습니다: {src}")

    raw = src.read_text(encoding="utf-8")
    cleaned = clean(raw)

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / "cleaned.txt"
    out.write_text(cleaned, encoding="utf-8")

    print(f"[clean] source={src}")
    print(f"[clean] before : {len(raw):>7} chars, {len(raw.splitlines()):>5} lines")
    print(f"[clean] after  : {len(cleaned):>7} chars, {len(cleaned.splitlines()):>5} lines")
    print(f"[clean] saved -> {out}")


if __name__ == "__main__":
    main()
