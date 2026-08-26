# 학습 데이터 빌드: sft-v1

- 교사 모델: gemini-2.5-flash
- 시나리오 106건 중 채택 100건 (94%)
- train 85 / valid 15

| 탈락 사유 | 건수 |
|---|---|
| verdict | 5 |
| citation | 1 |

### 탈락 상세

- `monitor-error-budget-burn-slow-settlement-async-unrelated-1092` [verdict] 기대 판정 아니오인데 정답은 예
- `monitor-error-spike-nunchi-press-partial-relevance-1058` [verdict] 기대 판정 예인데 정답은 아니오
- `monitor-error-spike-outbox-racinggame-partial-relevance-1074` [verdict] 기대 판정 예인데 정답은 아니오
- `monitor-error-spike-partial-relevance-907` [citation] 인용문이 로그에 없음: [2026-08-26 16:22:07.845] [ERROR] [14910ef3b40455581e0c94e7f
- `monitor-outbox-dead-letter-near-miss-919` [verdict] 기대 판정 아니오인데 정답은 예
- `monitor-outbox-dead-letter-settlement-consume-near-miss-1084` [verdict] 기대 판정 아니오인데 정답은 예
