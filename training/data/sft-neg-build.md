# 학습 데이터 빌드: sft-neg

- 교사 모델: gemini-2.5-flash
- 시나리오 41건 중 채택 35건 (85%)
- train 30 / valid 5

| 탈락 사유 | 건수 |
|---|---|
| verdict | 6 |

### 탈락 상세

- `monitor-error-budget-slow-unrelated-2001` [verdict] 기대 판정 아니오인데 정답은 예
- `monitor-error-spike-sparse-container-check-single-2035` [verdict] 기대 판정 아니오인데 정답은 예
- `monitor-outbox-dead-letter-consumer-side-near-miss-2020` [verdict] 기대 판정 아니오인데 정답은 예
- `monitor-outbox-dead-letter-settlement-path-near-miss-2029` [verdict] 기대 판정 아니오인데 정답은 예
- `monitor-redis-backlog-cardgame-blindtimer-container-near-miss-2028` [verdict] 기대 판정 아니오인데 정답은 예
- `monitor-redis-backlog-nunchi-settlement-near-miss-2026` [verdict] 기대 판정 아니오인데 정답은 예
