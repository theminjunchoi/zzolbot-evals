## 합성 필터 통계

- 생성 시도: 8건, 생존: 5건 (62%)

| 검증기 | 탈락 건수 |
|---|---|
| log-line | 2 |
| timestamp | 2 |

### 탈락 사유 상세

- `monitor-outbox-deadletter-high-positive-dense-1` [log-line] 로그 1: 실존하지 않는 스레드명: pool-1-1-thread-2; 로그 3: 실존하지 않는 스레드명: pool-1-1-thread-4; 로그 5: 실존하지 않는 스레드명: pool-1-1-thread-2; 로그 7: 실존하지 않는 스레드명: pool-1-1-thread-4
- `monitor-app-error-log-spike-stale-reingested-3` [timestamp] 로그 시각이 오름차순이 아님
- `monitor-redis-stream-e2e-latency-high-partial-relevance-5` [log-line] 로그 0: 실존하지 않는 스레드명: redis-stream-thread-pool-settlement:result-1; 로그 1: 실존하지 않는 스레드명: redis-stream-thread-pool-settlement:result-2; 로그 2: 실존하지 않는 스레드명: redis-stream-thread-pool-room:join-1; 로그 3: 실존하지
- `monitor-redis-stream-e2e-latency-high-partial-relevance-5` [timestamp] 로그 시각이 오름차순이 아님
