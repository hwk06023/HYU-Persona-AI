"""CLI chat: persona + RAG (메모리 없음).

--persona my|example  : 01-prompt/my-prompt.txt 또는 prompt-example.txt
--data    raw|my      : Qdrant 컬렉션 persona_raw 또는 persona_my
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB_DIR = HERE / "qdrant_data"

CHAT_MODEL = "gpt-5"
EMBED_MODEL = "text-embedding-3-large"

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


def render(persona_xml: str, rag_chunks, recent_turns: str, user_input: str) -> str:
    """페르소나 XML의 4개 Jinja-style 슬롯을 실제 값으로 치환한다.
    Jinja2를 쓰지 않는 이유: 페르소나 본문에 literal `{{ ... }}` JSON 예시가 들어 있어
    템플릿 엔진을 통과시키면 파싱 에러가 난다.
    """
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
            f"먼저 `python 4_index.py --collection {collection}`을 실행하세요."
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
            f"`python 4_index.py --collection {collection}`을 실행하세요."
        )

    print(DIVIDER)
    print(f"persona={args.persona}  data={args.data}({collection})  top_k={args.top_k}  model={CHAT_MODEL}")
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
                print()

            system = render(persona, chunks, recent_turns="", user_input=user_input)
            reply = chat_once(openai_client, system, user_input)
            print(f"Assistant> {reply}")
            print(DIVIDER)
    finally:
        client_qd.close()


if __name__ == "__main__":
    main()
