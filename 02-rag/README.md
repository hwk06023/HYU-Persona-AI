# 02-rag

Vector DB 구축 + 페르소나 RAG 챗.

## 파이프라인 (Raw → Clean → Chunk → Embed → Index → Chat)

| 단계 | 스크립트 | input | output |
|---|---|---|---|
| Raw | (수동) | — | `data/raw_data.txt` |
| Clean | `1_clean.py` | `data/raw_data.txt` | `outputs/cleaned.txt` |
| Chunk | `2_chunk.py` *(agentic, gpt-5-mini)* | `outputs/cleaned.txt` | `outputs/chunks.jsonl` |
| Embed | `3_embed.py` *(text-embedding-3-large, 3072d)* | `outputs/chunks.jsonl` | `outputs/embeddings.jsonl` |
| Index | `4_index.py` | `outputs/embeddings.jsonl` | Qdrant 컬렉션 (`qdrant_data/`) |
| Chat | `./chat.sh` *(gpt-5)* | CLI 입력 | CLI 출력 + retrieved chunks |

## 기본 실행 (예시 데이터 = 난중일기 발췌)

```bash
python 1_clean.py --source raw
python 2_chunk.py
python 3_embed.py
python 4_index.py --collection persona_raw
./chat.sh                          # persona=my, data=raw
./chat.sh --persona example        # 이순신 페르소나로 챗
```

## 본인 데이터로 돌리기

1. `data/my_raw_data.txt`에 본인 텍스트 붙여넣기
2. 아래 실행:

```bash
python 1_clean.py --source my
python 2_chunk.py
python 3_embed.py
python 4_index.py --collection persona_my
./chat.sh --data my
```

## 옵션

- `chat.py --top-k N` : 검색 상위 N개 청크 (기본 5)
- `chat.py --hide-chunks` : 검색된 청크 표시 끄기

## Agentic chunking 동작

`cleaned.txt`를 토큰 단위로 잘라(`--window` 30k 기본, `--hop` 1k 기본 겹침) LLM에 통째로 넣고
의미 단위 청크 경계를 직접 결정하게 합니다. 윈도우 경계의 토픽 손실은 hop overlap으로 줄입니다.
중복 청크는 첫 200자 정규화 키로 dedupe.
