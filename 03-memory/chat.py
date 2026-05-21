"""CLI chat: persona + RAG + 직전 6턴 메모리 (FIFO).

02-rag/chat.py와 차이는 단 하나: 직전 6턴(User/Assistant 페어)을 deque로 보관하다가
페르소나의 <recent_conversation_turns> 슬롯에 매 턴 자동 주입한다.
6턴 초과분은 자동 폐기(first-in-first-out).

Qdrant 인덱스는 02-rag/qdrant_data/ 를 그대로 재사용한다. (재인덱싱 불필요)
"""
import argparse
import json
import os
from collections import deque
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB_DIR = ROOT / "02-rag" / "qdrant_data"   # 02의 인덱스 재사용

CHAT_MODEL = "gpt-5"
EMBED_MODEL = "text-embedding-3-large"
MAX_TURNS = 6

PERSONA_FILES = {
    "my": ROOT / "01-prompt" / "my-prompt.txt",
    "example": ROOT / "01-prompt" / "prompt-example.txt",
}
COLLECTION_FOR = {
    "raw": "persona_raw",
    "my": "persona_my",
}

DIVIDER = "─" * 60


def load_persona(name: str) -> str:
    p = PERSONA_FILES[name]
    if not p.exists():
        raise SystemExit(
            f"Persona 파일이 없습니다: {p}\n"
            f"먼저 `01-prompt/generate_persona.py`를 실행하세요."
        )
    return p.read_text(encoding="utf-8")


def search(client_qd: QdrantClient, openai_client: OpenAI, collection: str, query: str, top_k: int):
    emb = openai_client.embeddings.create(model=EMBED_MODEL, input=[query]).data[0].embedding
    result = client_qd.query_points(
        collection_name=collection,
        query=emb,
        limit=top_k,
    )
    points = result.points if hasattr(result, "points") else result
    return [{"score": float(p.score), "text": p.payload.get("text", "")} for p in points]


def format_turns(turns: deque) -> str:
    if not turns:
        return ""
    parts = [f"User: {u}\nAssistant: {a}" for u, a in turns]
    return "\n\n".join(parts)


def render(persona_xml: str, rag_chunks, recent_turns: str, user_input: str) -> str:
    """페르소나 XML의 4개 슬롯을 단순 치환. (Jinja2를 안 쓰는 이유는 02-rag/chat.py 참조.)"""
    out = persona_xml
    out = out.replace("{{ rag_chunks_json }}", json.dumps(rag_chunks, ensure_ascii=False))
    out = out.replace("{{ user_long_term_summary }}", "")
    out = out.replace("{{ recent_conversation_turns }}", recent_turns)
    out = out.replace("{{ user_input }}", user_input)
    return out


def chat_once(openai_client: OpenAI, system_prompt: str, user_input: str) -> str:
    resp = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
    )
    return resp.choices[0].message.content or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", choices=["my", "example"], default="my")
    ap.add_argument("--data", choices=["raw", "my"], default="raw")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--hide-chunks", action="store_true")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY가 .env에 없습니다.")

    persona = load_persona(args.persona)
    collection = COLLECTION_FOR[args.data]

    if not DB_DIR.exists():
        raise SystemExit(
            f"Qdrant 데이터가 없습니다: {DB_DIR}\n"
            f"먼저 02-rag/4_index.py를 실행하세요."
        )

    try:
        client_qd = QdrantClient(path=str(DB_DIR))
    except RuntimeError as e:
        if "already accessed" in str(e):
            raise SystemExit(
                f"Qdrant 디렉터리가 다른 프로세스에 의해 잠겨 있습니다: {DB_DIR}\n"
                f"다른 터미널에서 02-rag/chat.py 또는 03-memory/chat.py가 실행 중인지 확인하고 종료하세요.\n"
                f"(로컬 Qdrant는 한 번에 한 프로세스만 접근 가능)"
            )
        raise

    openai_client = OpenAI(api_key=api_key)

    if not client_qd.collection_exists(collection):
        raise SystemExit(
            f"컬렉션 '{collection}'이 없습니다.\n"
            f"02-rag에서 `python 4_index.py --collection {collection}` 실행 필요."
        )

    turns: deque = deque(maxlen=MAX_TURNS)

    print(DIVIDER)
    print(f"persona={args.persona}  data={args.data}({collection})  "
          f"top_k={args.top_k}  memory={MAX_TURNS}턴(FIFO)  model={CHAT_MODEL}")
    print("종료: exit / quit / Ctrl+D")
    print(DIVIDER)

    try:
        while True:
            try:
                user_input = input("You> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", ":q"}:
                break

            chunks = search(client_qd, openai_client, collection, user_input, args.top_k)
            if not args.hide_chunks:
                print(f"\n[retrieved {len(chunks)} chunks]")
                for i, c in enumerate(chunks):
                    preview = c["text"].replace("\n", " ")[:120]
                    print(f"  ({i+1}) score={c['score']:.3f}  {preview}...")

                print(f"\n[memory {len(turns)}/{MAX_TURNS} turns]")
                if not turns:
                    print("  (비어 있음)")
                else:
                    for i, (u, a) in enumerate(turns, start=1):
                        print(f"  --- turn {i} ---")
                        print(f"    User      : {u[:200]}")
                        print(f"    Assistant : {a[:200].replace(chr(10), ' ')}")
                print()

            recent = format_turns(turns)
            system = render(persona, chunks, recent_turns=recent, user_input=user_input)
            reply = chat_once(openai_client, system, user_input)
            print(f"Assistant> {reply}")
            print(DIVIDER)

            turns.append((user_input, reply))
    finally:
        client_qd.close()


if __name__ == "__main__":
    main()
