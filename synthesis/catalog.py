"""실제 시스템에서 검증된 사실 목록.

시나리오 합성과 검증이 공유하는 단일 출처다. 여기 없는 알림, 로거, 메시지 형식은
실제 시스템에 존재하지 않는 것으로 간주하고 후보에서 탈락시킨다.
출처: zzol 백엔드 코드와 모니터링 룰 파일 실측 (2026-08-26 기준).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AlertRule:
    alertname: str
    severity: str
    required_labels: dict[str, str] = field(default_factory=dict)
    optional_labels: tuple[str, ...] = ()


# AppInstanceDown은 의도적으로 제외한다: zzolbot이 prod 앱 내부 모듈이라
# prod 전체 다운 시 웹훅을 받을 수 없어, 봇이 분석하는 상황 자체가 성립하지 않는다.
ALERT_RULES: dict[str, AlertRule] = {r.alertname: r for r in [
    AlertRule("DbConnectionPoolHigh", "warning", {"job": "prod-app"}),
    AlertRule("RedisStreamBacklogHigh", "warning", {"job": "prod-app"}),
    AlertRule("RedisStreamE2eLatencyHigh", "warning", {"job": "prod-app"}),
    AlertRule("OutboxDeadLetterHigh", "warning", {"job": "prod-app"}),
    AlertRule("Http5xxRatioHigh", "critical", {"job": "prod-app"}),
    AlertRule("JvmHeapUsageHigh", "critical", {"job": "prod-app"}),
    AlertRule("AppErrorLogSpike", "warning", {"job": "prod-app"}),
    # MassIpBlockingSpike는 job 라벨을 필수로 두지 않는다: #1592 재현 시드가
    # 당시(by(job) 누락 버그 시절) payload를 그대로 쓰기 때문이다.
    AlertRule("MassIpBlockingSpike", "critical", {}, ("job", "incident_group")),
    AlertRule("IpBanRateSpike", "warning", {"job": "prod-app", "incident_group": "ip-blocking"}),
    AlertRule("WsHandshakeProbeFailed", "critical", {"job": "blackbox-ws"}, ("edge",)),
    AlertRule("WsConnectionFailuresHigh", "warning", {"job": "prod-app"}),
    AlertRule("WsInboundLatencyHigh", "critical", {"job": "prod-app"}),
    AlertRule("LoginSuccessDroppedToZero", "critical", {"job": "prod-app"}, ("provider",)),
    AlertRule("CircuitBreakerOpen", "critical", {"job": "prod-app"}, ("name", "state")),
    AlertRule("MonitoringTargetDown", "warning", {}, ("job", "instance", "env")),
    AlertRule("AlloyDown", "warning", {"job": "alloy"}, ("env",)),
    AlertRule("DiskUsageHigh", "warning", {"job": "node"}),
    AlertRule("CpuUsageHigh", "critical", {}, ("job",)),
    AlertRule("ErrorBudgetBurnFast", "critical", {"job": "prod-app"}),
    AlertRule("ErrorBudgetBurnSlow", "warning", {"job": "prod-app"}),
]}


@dataclass(frozen=True)
class LogMessage:
    """실코드 log.error/warn의 포맷 문자열. {}는 임의 값 슬롯이다."""

    logger: str  # %logger{36} 축약형
    template: str
    level: str = "ERROR"


LOG_MESSAGES: tuple[LogMessage, ...] = (
    LogMessage("c.global.redis.EventDispatcher", "이벤트 처리 실패: consumer={}, message={}"),
    LogMessage("c.r.application.service.RoomService", "방 참가 비동기 처리 실패: eventId={}, joinCode={}, playerName={}"),
    LogMessage("c.r.i.messaging.RoomEventWaitManager", "방 이벤트 자동 정리 (실패): eventId={}"),
    LogMessage("c.s.i.c.SettlementStreamConsumer", "정산 처리 실패 — ACK 보류, 재전달 대기: recordId={}"),
    LogMessage("c.s.i.c.SettlementStreamConsumer", "정산 스트림 처리 중 오류가 발생했습니다."),
    LogMessage("c.s.i.c.SettlementPendingSweeper", "pending 정산 메시지 재처리 실패: recordId={}"),
    LogMessage("c.g.h.RedisStreamContainerRecovery", "Redis Stream container 상태 확인 중 예외: stream={}"),
    LogMessage("c.g.h.RedisStreamContainerRecovery", "Redis Stream container 복구 중 예외 발생: stream={}"),
    LogMessage("c.g.h.RedisStreamContainerRecovery", "Redis Stream container 복구 포기: stream={}. HealthIndicator에 DOWN 보고"),
    LogMessage("c.g.r.c.RedisStreamListenerStarter", "Redis Stream 처리 중 오류가 발생했습니다."),
    LogMessage("c.global.outbox.OutboxEventProcessor", "Outbox 이벤트 최대 재시도 초과, DEAD_LETTER 전환: id={}, streamKey={}"),
    LogMessage("c.web.exception.RestExceptionHandler", "method={} uri={} exception={} message={}"),
    LogMessage("c.n.i.m.c.NunchiCommandEventConsumer", "눈치게임 press 처리 중 오류: joinCode={}, playerName={}, eventId={}"),
    LogMessage("c.g.s.GameTaskSchedulerFactory", "[{}] 스케줄 실행 중 예외가 발생했습니다."),
    LogMessage("o.s.s.s.TaskUtils$LoggingErrorHandler", "Unexpected error occurred in scheduled task"),
    LogMessage("c.r.infra.OracleObjectStorageService", "Oracle Object Storage QR 코드 업로드 실패: contents={}, error={}"),
    LogMessage("c.r.infra.OracleObjectStorageService", "Oracle Object Storage Public URL 생성 실패: storageKey={}, error={}"),
    LogMessage("c.r.application.service.QrCodeService", "QR 코드 생성 실패: joinCode={}, error={}"),
    LogMessage("c.global.ipblock.IpBlockFilter", "차단된 IP 접근 시도: ip={} uri={}", "WARN"),
    LogMessage("c.global.ipblock.IpBlockFilter", "악성 경로 접근 감지 → IP 즉시 차단: ip={} uri={}", "WARN"),
    LogMessage("c.global.ipblock.IpBlockStore", "IP 차단 등록: ip={} ttl={}", "WARN"),
)

ALLOWED_LOGGERS: frozenset[str] = frozenset(m.logger for m in LOG_MESSAGES)

# 실제 스레드명 규칙. 무명 가상 스레드는 빈 문자열이다 (@Async qrCodeTaskExecutor 경로).
THREAD_PATTERNS: tuple[str, ...] = (
    r"http-nio-8080-exec-\d+",
    r"redis-stream-thread-pool-[a-z:]+\d+",
    r"pool-\d+-thread-\d+",
    r"[a-z]+-task-\d+",
    r"delay-removal-task-\d+",
    r"clientInboundChannel-\d+",
    r"",  # 무명 가상 스레드
)


# 실제 Redis Stream 키 11개 + 공유 풀 이름. 스레드명 redis-stream-thread-pool-{키}N의 {키}는 이 목록만 유효하다.
STREAM_POOL_NAMES: frozenset[str] = frozenset({
    "room", "room:join", "cardgame:select", "minigame", "racinggame", "speedtouch",
    "blindtimer", "blockstacking", "laddergame", "nunchi", "settlement:result", "concurrent",
})

# 로거가 실제로 돌 수 있는 스레드 계열. 코드의 실행 경로 실측 기준이다.
LOGGER_THREAD_AFFINITY: dict[str, tuple[str, ...]] = {
    "c.web.exception.RestExceptionHandler": ("exec",),
    "c.global.redis.EventDispatcher": ("stream",),
    "c.n.i.m.c.NunchiCommandEventConsumer": ("stream",),
    "c.s.i.c.SettlementStreamConsumer": ("stream",),
    "c.s.i.c.SettlementPendingSweeper": ("pool",),
    "c.g.h.RedisStreamContainerRecovery": ("pool",),
    "c.g.r.c.RedisStreamListenerStarter": ("stream",),
    "c.global.outbox.OutboxEventProcessor": ("pool",),
    "c.g.s.GameTaskSchedulerFactory": ("game-task",),
    "o.s.s.s.TaskUtils$LoggingErrorHandler": ("pool",),
    "c.r.infra.OracleObjectStorageService": ("virtual",),
    "c.r.application.service.QrCodeService": ("virtual",),
    "c.r.application.service.RoomService": ("stream", "pool"),
    "c.r.i.messaging.RoomEventWaitManager": ("stream", "pool"),
    "c.global.ipblock.IpBlockFilter": ("exec",),
    "c.global.ipblock.IpBlockStore": ("exec",),
}

# 알림별 summary/description 템플릿 ({}는 값 슬롯). 실제 룰 파일 annotation의 렌더 형태다.
# 복수 항목은 허용 변형(예: #1592 당시 payload 재현)이다.
ALERT_TEXT_TEMPLATES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "DbConnectionPoolHigh": (("DB 커넥션 풀 활성 > 8 (prod-app)",),
                             ("활성 연결 {}개 (최대 10). 슬로우 쿼리 또는 커넥션 누수 확인 필요.",)),
    "RedisStreamBacklogHigh": (("Redis Stream 적체 (length > 1000, prod-app)",),
                               ("스트림 길이가 {}. 컨슈머 처리 속도가 발행을 못 따라가고 있습니다.",)),
    "RedisStreamE2eLatencyHigh": (("Redis Stream E2E 지연 p95 > 500ms (prod-app)",),
                                  ("스트림 처리 p95 지연이 {}s. 컨슈머 처리 적체 또는 다운스트림(App Service) 지연 가능성.",)),
    "OutboxDeadLetterHigh": (("Outbox DEAD_LETTER 적체 (> 10, prod-app)",),
                             ("재시도 초과로 DEAD_LETTER 전환된 outbox 이벤트가 {}건. 다운스트림 발행 경로 점검 필요.",)),
    "Http5xxRatioHigh": (("HTTP 5xx 비율 5% 초과 (prod-app)",),
                         ("최근 5분 5xx 비율이 {}%. 서버 측 광범위 실패 가능성.",)),
    "JvmHeapUsageHigh": (("JVM 힙 사용률 > 85% (prod-app)",),
                         ("힙 사용률이 {}%. GC 오버헤드 증가 및 OOM 위험.",)),
    "AppErrorLogSpike": (("ERROR 로그 급증(최근 5분, prod-app)",),
                         ("ERROR 로그가 {}건(임계 30/5m)입니다. zzol-bot이 근본원인을 분석합니다.",)),
    "MassIpBlockingSpike": (("IP 차단 요청 급증 (prod-app)", "IP 차단 요청 급증"),
                            ("차단 요청이 {} req/s. 베이스라인(약 0.5 req/s) 대비 급증. 차단된 IP와 요청 경로를 확인.",
                             "차단 요청이 {} req/s. X-Forwarded-For 소실로 내부 IP가 BAN되는 패턴인지 즉시 확인.")),
    "IpBanRateSpike": (("신규 IP BAN 급증 (prod-app)",),
                       ("신규 BAN이 {} /s. 차단된 IP 대역과 접근 경로를 확인.",)),
    "WsHandshakeProbeFailed": (("WS 핸드셰이크 합성 프로브 실패 (edge=prod)",),
                               ("엣지(nginx:443)에서 WS 업그레이드(101)가 실패. nginx Upgrade/Connection 헤더 소실 의심. probe_failed_due_to_regex=1이면 TCP/TLS는 됐으나 101 미수신(=헤더 소실로 200 등 반환), 0이면 TCP/TLS 단계 실패(nginx 다운·인증서).",)),
    "WsConnectionFailuresHigh": (("WebSocket 연결 실패 급증 (prod-app)",),
                                 ("최근 5분 WS 연결 실패가 {}건 (임계 10). STOMP 연결 단계 실패 누적.",)),
    "WsInboundLatencyHigh": (("WebSocket 메시지 처리 p99 > 500ms (prod-app)",),
                             ("WS inbound p99 처리 시간이 {}s. 서비스 품질 저하 체감 수준.",)),
    "LoginSuccessDroppedToZero": (("{} 로그인 성공 0 (prod-app) — 시도는 계속됨",),
                                  ("최근 로그인 시도는 있으나 성공이 없다. redirect_uri(스킴/호스트)·provider 콘솔 등록·시크릿을 점검. 여러 provider 동시 발생 시 프록시/baseUrl 의심.",)),
    "CircuitBreakerOpen": (("서킷브레이커 OPEN (oracleStorage / prod-app)",),
                           ("서킷브레이커가 OPEN 상태입니다. 외부 서비스(OracleObjectStorage) 장애 확인 필요.",)),
    "MonitoringTargetDown": (("모니터링 타깃 down ({} / {})",),
                             ("{} 익스포터가 5분 이상 응답하지 않습니다. 이 타깃에 의존하는 알림이 평가 불능 상태일 수 있습니다.",)),
    "AlloyDown": (("Alloy 로그 수집기 down (prod)",),
                  ("prod Alloy가 5분 이상 메트릭을 내지 않습니다. 컨테이너 다운 또는 로그가 Loki로 인입되지 않는 상태일 수 있습니다.",)),
    "DiskUsageHigh": (("디스크 사용률 > 85%",),
                      ("디스크 사용률이 {}%. 로그 정리 또는 디스크 확장 필요.",)),
    "CpuUsageHigh": (("CPU 사용률 > 90% (5분 지속)",),
                     ("CPU 사용률이 {}%.",)),
    "ErrorBudgetBurnFast": (("에러버짓 빠른 소진 (SLO 99.5%, burn-rate 14.4×)",),
                            ("prod-app 5xx 비율이 1h·5m 양 창에서 7.2%를 초과. 약 2일이면 월간 에러버짓 전부 소진.",)),
    "ErrorBudgetBurnSlow": (("에러버짓 느린 소진 (SLO 99.5%, burn-rate 6×)",),
                            ("prod-app 5xx 비율이 6h·30m 양 창에서 3%를 초과. 누적 시 에러버짓 위협.",)),
}
