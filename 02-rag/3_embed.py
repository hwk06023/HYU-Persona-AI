"""Step 3: Embed chunks with OpenAI text-embedding-3-large.

input : outputs/chunks.jsonl
output: outputs/embeddings.jsonl  (한 줄에 {"id": int, "text": str, "vector": [float, ...]})
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT_DIR = HERE / "outputs"

MODEL = "text-embedding-3-large"
DIM = 3072
BATCH = 100
PRICE_PER_MTOK = 0.13  # USD


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(OUT_DIR / "chunks.jsonl"))
    ap.add_argument("--out", default=str(OUT_DIR / "embeddings.jsonl"))
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY가 .env에 없습니다.")

    inp = Path(args.inp)
    if not inp.exists():
        raise SystemExit(f"입력 파일이 없습니다: {inp}\n먼저 `python 2_chunk.py`를 실행하세요.")

    rows = [json.loads(ln) for ln in inp.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not rows:
        raise SystemExit(f"청크가 비어 있습니다: {inp}")
    print(f"[embed] input  : {len(rows)} chunks, model={MODEL}, dim={DIM}")

    client = OpenAI(api_key=api_key)
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)

    total_tokens = 0
    with out.open("w", encoding="utf-8") as f:
        for i in tqdm(range(0, len(rows), BATCH), desc="embedding"):
            batch = rows[i:i + BATCH]
            resp = client.embeddings.create(model=MODEL, input=[r["text"] for r in batch])
            total_tokens += resp.usage.total_tokens
            for r, d in zip(batch, resp.data):
                f.write(json.dumps(
                    {"id": r["id"], "text": r["text"], "vector": d.embedding},
                    ensure_ascii=False,
                ) + "\n")

    cost = total_tokens / 1_000_000 * PRICE_PER_MTOK
    print(f"[embed] tokens : {total_tokens} (est. cost: ${cost:.4f})")
    print(f"[embed] saved -> {out}")


if __name__ == "__main__":
    main()
