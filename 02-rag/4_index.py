"""Step 4: Index embeddings into a local Qdrant collection.

input : outputs/embeddings.jsonl
output: Qdrant 컬렉션 (qdrant_data/) — 컬렉션 이름은 --collection 으로 지정
"""
import argparse
import json
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from tqdm import tqdm

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "outputs"
DB_DIR = HERE / "qdrant_data"

DIM = 3072
UPSERT_BATCH = 256


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(OUT_DIR / "embeddings.jsonl"))
    ap.add_argument("--collection", default="persona_raw",
                    help="Qdrant 컬렉션 이름 (예: persona_raw, persona_my)")
    args = ap.parse_args()

    inp = Path(args.inp)
    if not inp.exists():
        raise SystemExit(f"입력 파일이 없습니다: {inp}\n먼저 `python 3_embed.py`를 실행하세요.")

    DB_DIR.mkdir(exist_ok=True)
    client = QdrantClient(path=str(DB_DIR))

    if client.collection_exists(args.collection):
        client.delete_collection(args.collection)
    client.create_collection(
        collection_name=args.collection,
        vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
    )

    points = []
    with inp.open(encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            r = json.loads(ln)
            points.append(PointStruct(
                id=int(r["id"]),
                vector=r["vector"],
                payload={"text": r["text"]},
            ))

    print(f"[index] collection={args.collection}, dim={DIM}, points={len(points)}")
    for i in tqdm(range(0, len(points), UPSERT_BATCH), desc="upserting"):
        client.upsert(collection_name=args.collection, points=points[i:i + UPSERT_BATCH])

    info = client.get_collection(args.collection)
    print(f"[index] indexed : {info.points_count} points")
    print(f"[index] saved -> {DB_DIR}/ (collection: {args.collection})")


if __name__ == "__main__":
    main()
