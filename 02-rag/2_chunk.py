"""Step 2: Agentic chunking.

윈도우로 잘라 LLM(gpt-5-mini)에 통째로 넣고 의미 단위 청크 경계를 잡는다.
윈도우 간 hop 만큼 겹쳐서 경계 손실을 줄인다.

input : outputs/cleaned.txt
output: outputs/chunks.jsonl  (한 줄에 {"id": int, "text": str})
"""
import argparse
import json
import os
import re
from pathlib import Path

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT_DIR = HERE / "outputs"

MODEL = "gpt-5-mini"
ENCODING = "cl100k_base"
WINDOW_TOKENS = 30_000     # LLM 입력 윈도우
HOP_TOKENS = 1_000         # 다음 윈도우와의 겹침

SYSTEM = (
    "You are a text chunking assistant.\n"
    "Split the user-provided text into semantically coherent chunks for retrieval.\n"
    "Rules:\n"
    "- Each chunk should be roughly 200-600 tokens (Korean characters count loosely).\n"
    "- Preserve original wording exactly. Do NOT summarize, translate, or rephrase.\n"
    "- Break at paragraph/topic boundaries, never mid-sentence.\n"
    "- Output strictly JSON: {\"chunks\": [{\"text\": \"...\"}, ...]} (Korean text kept verbatim)."
)


def slice_windows(tokens, encoder, size, hop):
    n = len(tokens)
    start = 0
    while start < n:
        end = min(start + size, n)
        yield start, encoder.decode(tokens[start:end])
        if end == n:
            return
        start = max(end - hop, start + 1)


def normalize_key(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()[:200]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(OUT_DIR / "cleaned.txt"))
    ap.add_argument("--out", default=str(OUT_DIR / "chunks.jsonl"))
    ap.add_argument("--window", type=int, default=WINDOW_TOKENS)
    ap.add_argument("--hop", type=int, default=HOP_TOKENS)
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY가 .env에 없습니다.")

    inp = Path(args.inp)
    if not inp.exists():
        raise SystemExit(f"입력 파일이 없습니다: {inp}\n먼저 `python 1_clean.py`를 실행하세요.")

    text = inp.read_text(encoding="utf-8")
    enc = tiktoken.get_encoding(ENCODING)
    tokens = enc.encode(text)
    print(f"[chunk] input  : {len(text):>7} chars, {len(tokens):>6} tokens")
    print(f"[chunk] window={args.window} tokens, hop={args.hop} tokens, model={MODEL}")

    client = OpenAI(api_key=api_key)
    seen = set()
    chunks = []

    windows = list(slice_windows(tokens, enc, args.window, args.hop))
    for _, window_text in tqdm(windows, desc="LLM chunking"):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": window_text},
            ],
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"[chunk] WARN: JSON parse failed: {e}")
            continue

        for c in data.get("chunks", []):
            t = (c.get("text") or "").strip()
            if not t:
                continue
            key = normalize_key(t)
            if key in seen:
                continue
            seen.add(key)
            chunks.append(t)

    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for i, t in enumerate(chunks):
            f.write(json.dumps({"id": i, "text": t}, ensure_ascii=False) + "\n")

    avg = sum(len(t) for t in chunks) / max(1, len(chunks))
    print(f"[chunk] output : {len(chunks)} chunks (avg {avg:.0f} chars)")
    print(f"[chunk] saved -> {out}")


if __name__ == "__main__":
    main()
