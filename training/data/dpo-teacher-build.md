# 학습 데이터 빌드: dpo-teacher

- 교사 모델: gemini-2.5-flash
- 시나리오 40건 중 채택 36건 (90%)
- train 35 / valid 1

| 탈락 사유 | 건수 |
|---|---|
| verdict | 3 |
| citation | 1 |

### 탈락 상세

- `monitor-5xx-logs-outside-query-window-rfta36` [verdict] 기대 판정 아니오인데 정답은 예
- `monitor-multi-stream-consumer-error-spike-rfta22` [verdict] 기대 판정 예인데 정답은 아니오
- `monitor-qr-upload-timeout-5xx-chain-rfta08` [citation] 인용문이 로그에 없음: [2026-08-26 13:25:16.330] [ERROR] [0a74b1254a8df23860375ae7c
- `monitor-settlement-backlog-nunchi-logs-rfta37` [verdict] 기대 판정 아니오인데 정답은 예
