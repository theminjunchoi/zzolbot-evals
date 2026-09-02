## 합성 필터 통계

- 생성 시도: 20건, 생존: 4건 (20%)

| 검증기 | 탈락 건수 |
|---|---|
| log-line | 6 |
| rubric | 5 |
| error-level | 4 |
| screen | 3 |

### 탈락 사유 상세

- `monitor-ip-ban-rate-spike-01` [log-line] 로그 0: 파일 로그 패턴 불일치; 로그 1: 파일 로그 패턴 불일치; 로그 2: 파일 로그 패턴 불일치; 로그 3: 파일 로그 패턴 불일치; 로그 4: 파일 로그 패턴 불일치; 로그 5: 파일 로그 패턴 불일치; 로그 6: 파일 로그 패턴 불일치; 로그 7: 파일 로그 패턴 불일치; 로그 8: 파일 로그 패턴 불일치
- `monitor-ws-connection-failures-high-2` [screen] 채점 기준은 로그가 'WebSocket 연결을 수립하거나 유지하지 못하게 된 과정을 명확히 보여준다'고 서술했으나, 실제 로그에는 WebSocket, WS, STOMP 또는 연결 실패와 관련된 직접적인 문자열이나 내용이 전혀 없습니다. 로그는 Redis Stream 컨테이너 장애와 이벤트 처리 실패를 보여줄 뿐입니다.
- `monitor-ip-ban-rate-spike-03` [error-level] 로그 0: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 1: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 2: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 3: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 4: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 5: 봇 입력은 ERROR만 도달 가능한데 WARN
- `monitor-ws-connection-failures-high-4` [screen] 채점 기준은 MiniGameStartConsumer가 '동일한 이벤트' 처리 시 지속적으로 실패한다고 서술했지만, 실제 로그에는 각기 다른 joinCode와 eventId를 가진 '다른 이벤트'들이 실패하고 있습니다.
- `monitor-ip-ban-rate-spike-05` [error-level] 로그 0: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 1: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 2: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 3: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 4: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 5: 봇 입력은 ERROR만 도달 가능한데 WARN
- `monitor-ip-ban-rate-spike-8` [error-level] 로그 0: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 1: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 2: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 3: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 4: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그 5: 봇 입력은 ERROR만 도달 가능한데 WARN; 로그
- `monitor-ws-connection-failure-9` [screen] 채점 기준은 로그가 'WebSocket 세션 유지가 불가능한 환경임을 나타낸다'고 서술했지만, 실제 로그에는 'WebSocket'이나 'STOMP' 등 WebSocket 연결 실패와 직접 관련된 용어가 전혀 없습니다.
- `monitor-cpu-usage-high-10` [log-line] 로그 1: o.s.s.s.TaskUtils$LoggingErrorHandler는 ('pool',) 스레드에서 돌지만 game-task(nunchi-task-1)에 있음; 로그 3: o.s.s.s.TaskUtils$LoggingErrorHandler는 ('pool',) 스레드에서 돌지만 game-task(nunchi-task-1)에 있음; 로그 5: o.s.
- `monitor-ip-ban-rate-spike-12` [log-line] 로그 0: 파일 로그 패턴 불일치
- `monitor-ip-ban-rate-spike-12` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-error-budget-burn-fast-13` [log-line] 로그 1: c.s.i.c.SettlementPendingSweeper는 ('pool',) 스레드에서 돌지만 stream(redis-stream-thread-pool-settlement:result1)에 있음
- `monitor-cpu-usage-high-14` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-cpu-usage-high-15` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-error-budget-burn-fast-16` [rubric] rubric에 정답/오답 조건이 없음
- `monitor-ip-ban-rate-spike-17` [log-line] 로그 0: c.s.i.c.SettlementStreamConsumer는 ('stream',) 스레드에서 돌지만 pool(pool-3-thread-2)에 있음
- `monitor-ip-ban-rate-spike-17` [error-level] 로그 2: 봇 입력은 ERROR만 도달 가능한데 WARN
- `monitor-cpu-usage-high-18` [log-line] 로그 0: c.g.s.GameTaskSchedulerFactory는 ('game-task',) 스레드에서 돌지만 pool(pool-5-thread-2)에 있음
- `monitor-ws-connection-unrelated-trap-19` [rubric] rubric에 정답/오답 조건이 없음
