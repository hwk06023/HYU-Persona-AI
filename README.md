# HYU-Persona-AI

페르소나 챗봇을 단계적으로 만들어보는 실습 키트.

```
01-prompt  →  02-rag  →  03-memory
(prompt)     (RAG)        (conversation memory)
```

---

## 0. 환경 세팅 (한 번만)

```bash
./setup.sh
source .venv/bin/activate
```

`.env`에 OpenAI API 키가 있어야 합니다.

```
OPENAI_API_KEY=sk-...
```

---

## 1. `01-prompt/` — 내 페르소나 프롬프트 만들기

Meta-prompt에 자기 brief를 태워 production-grade 페르소나 XML을 생성합니다.

| | input | output |
|---|---|---|
| **생성** | `01-prompt/my-brief.txt` (직접 작성) | `01-prompt/my-prompt.txt` |

```bash
cd 01-prompt
# my-brief.txt 채우기
python generate_persona.py
```

---

## 2. `02-rag/` — Vector DB 구축 + RAG 챗

`Raw → Clean → Chunk → Embed → Index → Chat` 5단계 + 챗.

| 단계 | 스크립트 | input | output |
|---|---|---|---|
| Raw | (수동) | — | `data/raw_data.txt` (난중일기 발췌 샘플 포함) |
| Clean | `1_clean.py` | `data/raw_data.txt` | `outputs/cleaned.txt` |
| Chunk | `2_chunk.py` (agentic, gpt-5-mini) | `outputs/cleaned.txt` | `outputs/chunks.jsonl` |
| Embed | `3_embed.py` (text-embedding-3-large) | `outputs/chunks.jsonl` | `outputs/embeddings.jsonl` |
| Index | `4_index.py` | `outputs/embeddings.jsonl` | Qdrant 컬렉션 (`qdrant_data/`) |
| Chat | `./chat.sh` | (CLI 입력) | (CLI 출력 + retrieved chunks 표시) |

```bash
cd 02-rag            # 루트에서 시작했다면
# 또는
cd ../02-rag         # 01-prompt 안에 있다면

python 1_clean.py --source raw
python 2_chunk.py
python 3_embed.py
python 4_index.py --collection persona_raw
./chat.sh                          # 본인 페르소나 + 예시 데이터
./chat.sh --persona example        # 이순신 페르소나로 챗
```

본인 데이터로 돌리고 싶으면 `data/my_raw_data.txt`에 텍스트를 붙여넣고:
```bash
python 1_clean.py --source my
python 2_chunk.py
python 3_embed.py
python 4_index.py --collection persona_my
./chat.sh --data my
```

---

## 3. `03-memory/` — 직전 6턴 대화 메모리

02와 동일한 RAG 위에 직전 6턴 대화를 system prompt에 자동 주입 (FIFO, 6턴 초과분은 버림). Qdrant 인덱스는 02 것을 그대로 재사용합니다.

```bash
cd 03-memory         # 루트에서 시작했다면
# 또는
cd ../03-memory      # 02-rag 안에 있다면

./chat.sh                          # 본인 페르소나 + 예시 데이터 + 6턴 메모리
./chat.sh --persona example
./chat.sh --data my
```

---

## 사용 모델 / 비용 가이드

| 용도 | 모델 |
|---|---|
| 페르소나 생성 (01) | `gpt-5` |
| Agentic chunking (02) | `gpt-5-mini` |
| 임베딩 (02) | `text-embedding-3-large` (3072 dim) |
| 챗 응답 (02/03) | `gpt-5` |

1인 풀 파이프라인 1회 ~$0.30 내외.

---

## 트러블슈팅

- **`OPENAI_API_KEY` 없음** → `.env` 파일 확인
- **`my-prompt.txt not found`** → 먼저 `01-prompt/generate_persona.py` 실행
- **`Qdrant 데이터가 없습니다`** → 먼저 `02-rag/4_index.py` 실행
- **한글 깨짐** → 파일 인코딩 UTF-8 확인
- **`pip: command not found` / `No module named pip`** → `pip` 대신 아래 중 하나로 재시도
  - 평소 `python`으로 실행하는 분: `python -m pip install -r requirements.txt`
  - 평소 `python3`로 실행하는 분: `python3 -m pip install -r requirements.txt`
  - 각 스텝의 `python ...` 명령도 동일하게 본인 환경의 `python` 또는 `python3` 로 바꿔서 실행하세요.
- **`Storage folder ... is already accessed by another instance of Qdrant client`** → 로컬 Qdrant는 한 번에 한 프로세스만 접근 가능합니다. 다른 터미널에서 `02-rag/chat.py` 또는 `03-memory/chat.py`가 실행 중인지 확인하고 종료한 뒤 다시 실행하세요.
