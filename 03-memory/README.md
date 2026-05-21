# 03-memory

02-rag와의 **유일한 차이** = 직전 6턴 대화를 system prompt에 자동 주입 (FIFO, 7턴째부터 가장 오래된 턴 자동 폐기).

Qdrant 인덱스는 `02-rag/qdrant_data/` 를 그대로 재사용합니다. 재인덱싱 불필요.

```bash
./chat.sh                          # persona=my, data=raw
./chat.sh --persona example        # 이순신 페르소나
./chat.sh --data my                # 본인 데이터(persona_my 컬렉션)
```

02 챗과 같은 질문이라도, 직전 턴 맥락을 참고해 답이 달라지는지 비교해보세요.
