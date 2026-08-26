# zzolbot monitor 골든 시나리오 (독립 20종)

zzolbot 알림 분석 품질을 재기 위한 평가셋. worktree feat/1626의 기존 시드 5종에 의존하지 않는 **독립 완결 세트**다(기존 5종이 다루던 가치 있는 축인 타임스탬프 불일치, 희소 로그, 가설 주입은 더 정교한 버전으로 재작성해 포함). 작성일 2026-08-26.

## 스키마

feat/1626 `MonitorEvalSeedInitializer.SeedFile`과 동일:
`{name, question, rubric, source, alert{alertname, severity, fingerprint, summary, description, labels}, logSamples[], logEnvironment}`

- judge는 로그 원문을 보지 못하므로 rubric이 사실관계를 서술한다.
- rubric은 flatten 계약 문자열(`'근거 발견: 예/아니오'`)을 그대로 인용하고, 정답 조건과 오답 조건 2단으로 쓴다.

## 시나리오 20종

| # | name | alertname | 기대 | 축 |
|---|---|---|---|---|
| 1 | monitor-db-pool-exhaustion-request-timeouts | DbConnectionPoolHigh | 예 | DB 커넥션 풀 포화 |
| 2 | monitor-db-pool-high-unrelated-game-errors | DbConnectionPoolHigh | 아니오 | 무관 로그 함정 (1의 대조군) |
| 3 | monitor-settlement-backlog-consumer-failures | RedisStreamBacklogHigh | 예 | 컨슈머 그룹 소비 정체 |
| 4 | monitor-stream-latency-container-recovery | RedisStreamE2eLatencyHigh | 예 | 리스너 컨테이너 다운 |
| 5 | monitor-heap-high-sparse-unrelated-errors | JvmHeapUsageHigh | 아니오 | 희소+무관 로그 함정 |
| 6 | monitor-5xx-redis-connection-failure | Http5xxRatioHigh | 예 | Redis 장애 전파 |
| 7 | monitor-outbox-deadletter-publish-failures | OutboxDeadLetterHigh | 예 | Outbox 재시도 초과 |
| 8 | monitor-ws-probe-failed-edge-layer | WsHandshakeProbeFailed | 아니오 | 레이어 구분 (엣지 vs 앱) |
| 9 | monitor-error-spike-nunchi-consumer | AppErrorLogSpike | 예 | 스파이크 positive (과잉 보수화 방지) |
| 10 | monitor-mass-ip-blocking-description-echo-trap | MassIpBlockingSpike | 아니오 | description 가설 주입 (#1592 재현) |
| 11 | monitor-error-spike-stale-reingested-v2 | AppErrorLogSpike | 아니오 | 시간적 접지 (재적재 아티팩트) |
| 12 | monitor-error-spike-roomjoin-current-window | AppErrorLogSpike | 예 | 11의 대조군 (같은 내용, 정합 시각) |
| 13 | monitor-error-spike-sparse-two-lines | AppErrorLogSpike | 아니오 | 양적 접지 (2줄 vs 38건) |
| 14 | monitor-error-spike-cardgame-select-burst | AppErrorLogSpike | 예 | 스파이크 positive (10과 동일 증거, 다른 알림) |
| 15 | monitor-circuit-breaker-open-qr-uploads | CircuitBreakerOpen | 예 | 외부 의존성 장애 |
| 16 | monitor-login-drop-unrelated-logs | LoginSuccessDroppedToZero | 아니오 | 무관 로그 (인증 레이어) |
| 17 | monitor-alloy-down-observability-layer | AlloyDown | 아니오 | 관측 스택 자체 장애 (로그 수집기) |
| 18 | monitor-target-down-mysql-exporter | MonitoringTargetDown | 아니오 | 관측 스택 자체 장애 |
| 19 | monitor-5xx-db-connection-failure | Http5xxRatioHigh | 예 | DB 장애 전파 (6과 원인 판별) |
| 20 | monitor-disk-high-unrelated-app-logs | DiskUsageHigh | 아니오 | 호스트 레이어 |

판정 분포: **예 10 / 아니오 10.** 알림 종류 15개.

### 대조군 설계 (같은 조건에서 한 변수만 바꿈)

- 1 vs 2: 같은 알림(DbConnectionPoolHigh), 로그만 관련/무관 → 알림 종류가 아니라 로그를 보고 판단하는지
- 11 vs 12: 같은 로그 내용(방 참가 실패), 타임스탬프만 불일치/정합 → 시간적 접지를 하는지
- 6 vs 19: 같은 알림(Http5xxRatioHigh), 원인만 Redis/DB → 근거에서 원인을 판별하는지
- 10 vs 14: 같은 증거 계열(카드게임 select 실패), 알림만 IP/에러스파이크 → 알림과의 관련성으로 판정을 뒤집는지
- 9, 12, 14 (스파이크 positive들) vs 11, 13 (스파이크 negative들) → "스파이크는 무조건 근거 없음"으로 과잉 학습되는 것 방지

## 정확성 계약 (전 시나리오가 지키는 실제 시스템 값)

- **로그 포맷**: logback FILE 패턴 `[yyyy-MM-dd HH:mm:ss.SSS] [LEVEL] [traceId32,spanId16] --- [thread] logger{36} : msg`. 스케줄 스레드는 `[,]`, 이름 없는 가상 스레드(@Async qrCodeTaskExecutor)는 `[]`.
- **로거 축약**: `%logger{36}` 알고리즘으로 계산, 패키지는 전부 grep 실측 (`c.web.exception.RestExceptionHandler`, `c.s.i.c.SettlementStreamConsumer`, `c.g.h.RedisStreamContainerRecovery`, `c.n.i.m.c.NunchiCommandEventConsumer`, `c.r.application.service.QrCodeService`, `c.r.infra.OracleObjectStorageService` 등).
- **로그 메시지**: 실코드 log.error 포맷 문자열만 사용. 이벤트 필드도 실제 record 정의(RoomJoinEvent[eventId, timestamp, joinCode, guestName, userId], SelectCardCommandEvent[... cardIndex]).
- **스레드명**: `redis-stream-thread-pool-{streamKey}N`, `http-nio-8080-exec-N`, `nunchi-task-N`, `pool-N-thread-M`, `[]`(무명 가상 스레드).
- **알림 payload**: 실제 룰 파일 annotation 템플릿의 렌더값. labels도 룰/메트릭의 실제 라벨 (job=prod-app, incident_group=ip-blocking, name=oracleStorage+state=open, job=blackbox-ws+edge=prod, job=mysql-exporter+instance=prod-mysql+env=prod, job=node, provider=kakao).
- **URI**: RoomRestController 실제 매핑만 (`/rooms`, `/rooms/check-joinCode`, `/rooms/check-guestName`, `/rooms/{joinCode}/probabilities`, `/rooms/nickname/random`).
- **인프라 사실**: HikariCP 기본 10 / 1000 초과 가능한 스트림은 settlement:result뿐(max-length 10000, 나머지 100 트리밍) / 방 상태와 세션은 Redis라 Redis 장애는 광범위 5xx / Outbox MAX_RETRY 10 / nginx 로그는 Loki 미적재 / 서킷브레이커 인스턴스명 oracleStorage / QR 딥링크 `https://www.zzol.site/join/` / CB open 메시지는 resilience4j 실제 포맷.
- #10의 description은 #1592 당시 룰 원문(10.54 req/s는 실측치), 로그 4줄은 Loki 복원 실로그 재사용.

## 실행 방법 (자바 하네스 리허설)

1. JSON들을 worktree `backend/zzolbot/src/main/resources/eval/monitor-seed/`에 복사 (커밋 금지)
2. `backend/`에서 `docker compose up -d` 후 `SPRING_PROFILES_ACTIVE=local SPRING_DOCKER_COMPOSE_ENABLED=false ./gradlew :app:bootRun` (GEMINI 키는 ~/.zzol/zzolbot-local.env)
3. `/admin/login`에서 CSRF hidden 토큰 얻어 admin/1234 로그인 → `/admin/zzolbot` 페이지의 meta CSRF로 `POST /admin/zzolbot/eval/runs {"label":"...","repeats":1,"kind":"monitor"}`
4. 완료 후 `/admin/zzolbot/eval/runs/{id}` 결과 수집 → reports/에 저장 → worktree 시드 삭제로 원복
- 주의: worktree에 시드를 두고 테스트를 돌리면 `MonitorEvalSeedInitializerTest.SEED_COUNT` 실패. 앱 실행만 할 것.
- 주의: worktree 기존 시드 5종이 함께 적재되므로, 이 20종만 측정하려면 결과에서 name으로 필터.

## 이력

- 2026-08-26: 10종으로 자바 리허설 1회 측정(13/15, 신규 10종 전부 PASS) - reports/01-자바-하네스-리허설.md
- 2026-08-26: 20종으로 확장(11~20 추가). 기존 worktree 5종은 품질 문제로 개인 셋에서 제외하고 축만 재작성.
- 2026-08-26: 전수 재검증 후 수정.
  - 포이즌 메시지 시나리오 폐기: 컨슈머 그룹은 미ACK 메시지를 컨테이너가 재전달하지 않고 sweeper(30초 주기, 최대 5회)만 재처리하므로, 포이즌 1건이 만들 수 있는 ERROR는 6줄 수준이라 30건/5분 스파이크가 물리적으로 불가능. → 카드게임 select 버스트(14)로 교체.
  - AppInstanceDown 폐기: zzolbot이 prod 앱 내부 모듈이라 prod 전체 다운 시 웹훅 수신 자체가 불가능한 모순. → AlloyDown(17)으로 교체.
  - CB 시나리오(15): fallback이 CallNotPermittedException을 WARN으로 남기고 한국어 메시지로 래핑함을 확인, ERROR 라인을 실제 문자열로 정정.
  - 1, 19: check-joinCode와 probabilities는 Redis 경로라 트랜잭션 예외 불가 → POST /rooms(createRoom @Transactional 확인)로 정정.
  - 13, 20: QrCodeService는 래핑된 InfrastructureException 메시지를 찍으므로 Read timed out 원문은 OracleObjectStorageService 라인으로 이동.
  - 10: #1592 당시 룰은 by(job)이 없어(그게 버그) 알림에 job 라벨이 없었음 → 라벨을 당시 형태로 정정.
  - 알려진 뉘앙스(수용): 3번의 XLEN은 소비가 아니라 발행 누적을 반영하지만(트리밍은 발행측 max-length뿐), 룰 자체가 "컨슈머 적체" 프레임으로 작성돼 있고 로그 증거상 최선의 진단은 컨슈머 정체이므로 유지.
