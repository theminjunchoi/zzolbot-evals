## 합성 필터 통계

- 생성 시도: 7건, 생존: 3건 (43%)

| 검증기 | 탈락 건수 |
|---|---|
| slot-value | 2 |
| log-line | 2 |
| rubric | 1 |

### 탈락 사유 상세

- `monitor-app-error-log-spike-stale-reingested-03` [slot-value] 로그 3: 실존하지 않는 streamKey: settlement-stream; 로그 4: 실존하지 않는 streamKey: settlement-stream; 로그 5: 실존하지 않는 streamKey: settlement-stream
- `monitor-app-error-log-spike-sparse-evidence-04` [log-line] 로그 0: 파일 로그 패턴 불일치
- `monitor-app-error-log-spike-sparse-evidence-04` [slot-value] 로그 1: 실존하지 않는 stream: settlement
- `monitor-redis-stream-latency-partial-relevance-05` [log-line] 로그 1: 파일 로그 패턴 불일치; 로그 3: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 6: 파일 로그 패턴 불일치; 로그 7: 파일 로그 패턴 불일치
- `monitor-redis-stream-backlog-high-unrelated-stream` [rubric] rubric에 정답/오답 조건이 없음
