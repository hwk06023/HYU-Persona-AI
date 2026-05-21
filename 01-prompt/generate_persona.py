"""Generate a personal persona prompt by feeding my-brief.txt into meta-prompt.txt."""
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

META_PROMPT_PATH = HERE / "meta-prompt.txt"
BRIEF_PATH = HERE / "my-brief.txt"
OUTPUT_PATH = HERE / "my-prompt.txt"

MODEL = "gpt-5"


def extract_xml(raw: str) -> str:
    m = re.search(r"```xml\s*(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    return raw.strip()


def main():
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY가 .env에 없습니다.")

    if not META_PROMPT_PATH.exists():
        raise SystemExit(f"meta-prompt가 없습니다: {META_PROMPT_PATH}")
    if not BRIEF_PATH.exists():
        raise SystemExit(f"my-brief.txt가 없습니다: {BRIEF_PATH}")

    meta_prompt = META_PROMPT_PATH.read_text(encoding="utf-8")
    brief = BRIEF_PATH.read_text(encoding="utf-8").strip()

    body_lines = [ln for ln in brief.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not body_lines:
        raise SystemExit("my-brief.txt가 비어 있습니다. 먼저 채워주세요.")

    print(f"[generate_persona] model={MODEL}, brief={len(brief)} chars")

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": meta_prompt},
            {"role": "user", "content": brief},
        ],
    )
    raw = resp.choices[0].message.content or ""
    persona = extract_xml(raw)

    OUTPUT_PATH.write_text(persona, encoding="utf-8")

    print(f"[generate_persona] saved -> {OUTPUT_PATH} ({len(persona)} chars)")
    usage = getattr(resp, "usage", None)
    if usage:
        print(f"[generate_persona] tokens: prompt={usage.prompt_tokens}, "
              f"completion={usage.completion_tokens}, total={usage.total_tokens}")


if __name__ == "__main__":
    main()
