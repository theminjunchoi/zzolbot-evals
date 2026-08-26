## 합성 필터 통계

- 생성 시도: 42건, 생존: 10건 (24%)

| 검증기 | 탈락 건수 |
|---|---|
| log-line | 13 |
| slot-value | 11 |
| rubric | 7 |
| generation | 3 |
| screen | 2 |
| duplicate | 2 |
| error-level | 2 |
| alert-text | 1 |

### 탈락 사유 상세

- `monitor-outbox-deadletter-high-1` [screen] 채점 기준은 로그가 '동일한 이벤트들을 반복 처리하다가' DEAD_LETTER로 전환했음을 보여준다고 서술했으나, 실제 로그에는 각기 다른 ID를 가진 이벤트들이 DEAD_LETTER로 전환된 내용만 있어 '동일한 이벤트'라는 서술과 모순됩니다.
- `(생성 실패 #2)` [generation] Extra data: line 30 column 1 (char 2338)
- `monitor-app-error-log-spike-3` [log-line] 로그 0: 파일 로그 패턴 불일치; 로그 1: 파일 로그 패턴 불일치; 로그 2: 파일 로그 패턴 불일치; 로그 3: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 5: 파일 로그 패턴 불일치
- `monitor-outbox-deadletter-high-4` [slot-value] 로그 0: 실존하지 않는 streamKey: room:event; 로그 1: 실존하지 않는 streamKey: room:event; 로그 4: 실존하지 않는 streamKey: room:event; 로그 5: 실존하지 않는 streamKey: room:event
- `monitor-redis-stream-e2e-latency-high` [log-line] 로그 0: 파일 로그 패턴 불일치; 로그 1: 파일 로그 패턴 불일치; 로그 2: 파일 로그 패턴 불일치; 로그 3: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 5: 파일 로그 패턴 불일치
- `monitor-login-success-dropped-to-zero-7` [alert-text] summary가 룰 템플릿과 다름: 로그인 성공 0 (prod-app) - 시도는 계속됨
- `monitor-login-success-dropped-to-zero-7` [log-line] 로그 1: c.s.i.c.SettlementStreamConsumer는 ('stream',) 스레드에서 돌지만 pool(pool-3-thread-5)에 있음; 로그 2: c.s.i.c.SettlementStreamConsumer는 ('stream',) 스레드에서 돌지만 pool(pool-3-thread-5)에 있음
- `monitor-login-success-dropped-to-zero-7` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-login-success-dropped-to-zero-8` [log-line] 로그 2: 파일 로그 패턴 불일치
- `monitor-ws-connection-failures-10` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-error-budget-burn-slow-12` [log-line] 로그 0: c.g.s.GameTaskSchedulerFactory는 ('game-task',) 스레드에서 돌지만 pool(pool-3-thread-2)에 있음
- `monitor-app-error-log-spike-13` [log-line] 로그 0: 파일 로그 패턴 불일치; 로그 2: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 6: 파일 로그 패턴 불일치
- `monitor-app-error-log-spike-13` [slot-value] 로그 5: 실존하지 않는 streamKey: settlement-stream
- `monitor-app-error-log-spike-15` [slot-value] 로그 4: 실존하지 않는 stream: order
- `(생성 실패 #16)` [generation] Extra data: line 32 column 1 (char 2315)
- `monitor-app-error-log-spike-17` [log-line] 로그 2: 파일 로그 패턴 불일치; 로그 5: 파일 로그 패턴 불일치
- `monitor-app-error-log-spike-17` [slot-value] 로그 4: 실존하지 않는 streamKey: game-events
- `monitor-app-error-log-spike-17` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-app-error-log-spike-17` [duplicate] 이름 중복: monitor-app-error-log-spike-17
- `monitor-app-error-log-spike-18` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-app-error-log-spike-19` [duplicate] 이름 중복: monitor-app-error-log-spike-19
- `monitor-ws-inbound-latency-high-21` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-app-error-log-spike-24` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-app-error-log-spike-25` [log-line] 로그 1: c.s.i.c.SettlementStreamConsumer는 ('stream',) 스레드에서 돌지만 pool(pool-1-thread-2)에 있음; 로그 2: c.s.i.c.SettlementStreamConsumer는 ('stream',) 스레드에서 돌지만 pool(pool-1-thread-2)에 있음; 로그 3: c.s.i.c.Settleme
- `monitor-app-error-log-spike-25` [error-level] 로그 0: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 5: 봇 입력은 ERROR만 도달 가능한데 WARN
- `monitor-app-error-log-spike-26` [log-line] 로그 6: c.r.application.service.RoomService는 ('stream', 'pool') 스레드에서 돌지만 exec(http-nio-8080-exec-12)에 있음
- `monitor-redis-stream-e2e-latency-28` [log-line] 로그 0: 파일 로그 패턴 불일치; 로그 2: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 5: c.global.ipblock.IpBlockStore는 ('exec',) 스레드에서 돌지만 virtual()에 있음; 로그 6: 파일 로그 패턴 불일치
- `monitor-redis-stream-e2e-latency-28` [error-level] 로그 1: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 5: 봇 입력은 ERROR만 도달 가능한데 WARN
- `monitor-5xx-partial-relevance-29` [screen] 채점 기준이 'OracleObjectStorageService 관련 QR 코드 생성 실패'를 언급했지만, 실제 로그에는 'OracleObjectStorageService'라는 컴포넌트명이 존재하지 않습니다.
- `monitor-5xx-partial-relevance-30` [log-line] 로그 2: c.n.i.m.c.NunchiCommandEventConsumer는 ('stream',) 스레드에서 돌지만 game-task(nunchi-task-1)에 있음
- `monitor-app-error-log-spike-31` [slot-value] 로그 4: 실존하지 않는 streamKey: nunchi-stream; 로그 5: 실존하지 않는 streamKey: nunchi-stream
- `monitor-redis-stream-e2e-latency-33` [log-line] 로그 0: 파일 로그 패턴 불일치; 로그 1: 파일 로그 패턴 불일치; 로그 2: 파일 로그 패턴 불일치; 로그 3: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 5: 파일 로그 패턴 불일치
- `monitor-redis-stream-e2e-latency-34` [slot-value] 로그 0: 실존하지 않는 stream: settlement; 로그 1: 실존하지 않는 stream: settlement
- `monitor-app-error-log-spike-36` [slot-value] 로그 5: 실존하지 않는 stream: ladder; 로그 6: 실존하지 않는 stream: ladder
- `monitor-db-connection-pool-37` [log-line] 로그 0: c.g.h.RedisStreamContainerRecovery는 ('pool',) 스레드에서 돌지만 stream(redis-stream-thread-pool-nunchi1)에 있음; 로그 1: 파일 로그 패턴 불일치; 로그 2: 파일 로그 패턴 불일치; 로그 3: 파일 로그 패턴 불일치
- `monitor-db-connection-pool-37` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-outbox-deadletter-near-miss-38` [slot-value] 로그 1: 실존하지 않는 stream: settlement
- `monitor-db-pool-near-miss-39` [slot-value] 로그 2: 실존하지 않는 streamKey: nunchi:press; 로그 3: 실존하지 않는 streamKey: nunchi:press
- `monitor-jvm-heap-usage-high-40` [slot-value] 로그 1: 실존하지 않는 stream: settlement
- `monitor-outbox-dead-letter-high-41` [slot-value] 로그 3: 실존하지 않는 stream: outbox
- `(생성 실패 #42)` [generation] Extra data: line 28 column 1 (char 2233)
