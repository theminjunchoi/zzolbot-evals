## 합성 필터 통계

- 생성 시도: 35건, 생존: 16건 (46%)

| 검증기 | 탈락 건수 |
|---|---|
| log-line | 9 |
| slot-value | 8 |
| rubric | 5 |
| generation | 2 |

### 탈락 사유 상세

- `monitor-app-error-log-spike-3` [slot-value] 로그 0: 실존하지 않는 stream: settlement; 로그 1: 실존하지 않는 stream: settlement; 로그 2: 실존하지 않는 stream: settlement
- `monitor-outbox-dead-letter-high-04` [slot-value] 로그 0: 실존하지 않는 streamKey: room-events; 로그 1: 실존하지 않는 streamKey: room-events; 로그 2: 실존하지 않는 streamKey: room-events; 로그 3: 실존하지 않는 streamKey: room-events; 로그 4: 실존하지 않는 streamKey: room-events; 로그 5: 실존하지
- `monitor-error-budget-burn-slow-10` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-app-error-log-spike-11` [slot-value] 로그 0: 실존하지 않는 stream: settlement; 로그 1: 실존하지 않는 stream: settlement; 로그 2: 실존하지 않는 stream: settlement
- `monitor-app-error-log-spike-12` [log-line] 로그 0: 파일 로그 패턴 불일치; 로그 2: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 6: 파일 로그 패턴 불일치
- `monitor-app-error-log-spike-12` [slot-value] 로그 5: 실존하지 않는 stream: game
- `monitor-app-error-log-spike-13` [log-line] 로그 0: c.g.s.GameTaskSchedulerFactory는 ('game-task',) 스레드에서 돌지만 pool(pool-1-thread-5)에 있음; 로그 6: 파일 로그 패턴 불일치
- `monitor-app-error-log-spike-13` [slot-value] 로그 4: 실존하지 않는 stream: settlement
- `monitor-app-error-log-spike-13` [rubric] rubric에 정답/오답 조건이 없음
- `(생성 실패 #14)` [generation] Extra data: line 32 column 1 (char 2212)
- `monitor-app-error-log-spike-stale-reingested-15` [log-line] 로그 0: 파일 로그 패턴 불일치; 로그 2: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 6: 파일 로그 패턴 불일치; 로그 7: 파일 로그 패턴 불일치
- `monitor-app-error-log-spike-stale-reingested-15` [slot-value] 로그 3: 실존하지 않는 stream: settlement
- `monitor-5xx-partial-relevance-21` [log-line] 로그 3: c.s.i.c.SettlementStreamConsumer는 ('stream',) 스레드에서 돌지만 pool(pool-2-thread-3)에 있음; 로그 6: c.s.i.c.SettlementStreamConsumer는 ('stream',) 스레드에서 돌지만 pool(pool-3-thread-1)에 있음
- `monitor-app-error-log-spike-22` [log-line] 로그 0: c.g.s.GameTaskSchedulerFactory는 ('game-task',) 스레드에서 돌지만 pool(pool-1-thread-5)에 있음
- `monitor-redis-stream-e2e-latency-25` [log-line] 로그 0: c.s.i.c.SettlementStreamConsumer는 ('stream',) 스레드에서 돌지만 pool(pool-1-thread-5)에 있음
- `monitor-app-error-log-spike-26` [log-line] 로그 3: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 6: 파일 로그 패턴 불일치; 로그 7: 파일 로그 패턴 불일치
- `monitor-app-error-log-spike-27` [log-line] 로그 3: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 5: 파일 로그 패턴 불일치
- `monitor-redis-stream-e2e-latency-28` [slot-value] 로그 0: 실존하지 않는 stream: settlement; 로그 1: 실존하지 않는 stream: settlement; 로그 2: 실존하지 않는 stream: settlement
- `(생성 실패 #29)` [generation] Extra data: line 32 column 1 (char 2303)
- `monitor-5xx-compound-cause-30` [log-line] 로그 3: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 5: 파일 로그 패턴 불일치; 로그 6: 파일 로그 패턴 불일치; 로그 7: 파일 로그 패턴 불일치
- `monitor-db-pool-high-near-miss-redis` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-redis-stream-backlog-high-unrelated-stream` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-db-pool-high-redis-stream-error` [slot-value] 로그 0: 실존하지 않는 stream: settlement; 로그 1: 실존하지 않는 stream: settlement; 로그 3: 실존하지 않는 stream: settlement
- `monitor-db-pool-high-redis-stream-error` [rubric] rubric에 정답/오답 조건이 없음
