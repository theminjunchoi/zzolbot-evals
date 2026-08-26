"""Gemini로 시나리오 후보를 생성한다. 정확성은 여기서 보장하지 않는다.

생성물은 반드시 validators를 통과해야 후보가 되고, 통과율과 탈락 사유는
FilterStats로 집계된다. 생성 프롬프트에는 검증된 카탈로그(알림 룰, 로그 형식)와
기존 골든셋 예시를 넣어 형식 준수율을 높인다.
"""

from __future__ import annotations

import json

from harness.domain import Scenario
from harness.llm import LlmJsonClient
from synthesis.axes import Axis
from synthesis.catalog import ALERT_RULES, ALERT_TEXT_TEMPLATES, LOG_MESSAGES, STREAM_POOL_NAMES

SYSTEM_INSTRUCTION = """\
너는 운영 모니터링 봇의 평가 시나리오를 만드는 합성 데이터 엔지니어다.
실제 시스템(zzol: 미니게임 추첨 서비스, Spring 백엔드)의 알림과 로그를 재현한
골든 시나리오를 JSON으로 생성한다.

반드시 지켜야 하는 형식:
1. 로그 한 줄 = "[yyyy-MM-dd HH:mm:ss.SSS] [ERROR|WARN] [<32자리hex트레이스,16자리hex스팬 또는 빈값>,] --- [<스레드명>] <로거축약형> : <메시지>"
   - 트레이스가 없으면 "[,]" 형태다. HTTP 요청 로그는 트레이스가 있고, 스케줄 스레드는 "[,]"다.
   - 스레드명과 로거와 메시지는 아래 카탈로그에 있는 것만 사용한다. 새로 지어내면 탈락한다.
2. 알림은 카탈로그의 alertname만 쓰고 severity와 라벨을 카탈로그와 일치시킨다.
3. rubric은 judge가 로그를 못 보므로 사실관계를 1문장으로 서술한 뒤,
   '근거 발견: 예' 또는 '근거 발견: 아니오' 중 기대 판정을 그대로 인용해 정답 조건을 쓰고,
   이어서 오답 조건을 쓴다.
4. question은 "알림 <Alertname>(<severity>)가 prod에서 발화했다 - <요지>. 봇에는 <입력 서술>이 주어졌다." 형식.
5. 출력은 JSON 객체 하나: {"name", "question", "rubric", "source": "MANUAL", "alert": {"alertname",
   "severity", "fingerprint", "summary", "description", "labels"}, "logSamples": [...],
   "logEnvironment": "prod", "expected": "예" 또는 "아니오", "axis": "<축 키>"}
6. name은 monitor-로 시작하는 소문자 케밥 케이스, fingerprint는 golden-gen-<축약어>-<숫자> 형식.
7. joinCode는 대문자 4자리, eventId는 UUID, 트레이스는 무작위 hex로 매번 다르게 만든다."""


def build_prompt(axis: Axis, alertname: str, exemplars: list[Scenario], ordinal: int) -> str:
    rule = ALERT_RULES[alertname]
    summary_templates, description_templates = ALERT_TEXT_TEMPLATES[alertname]
    required_labels = {"alertname": rule.alertname, "severity": rule.severity, **rule.required_labels}
    message_lines = [f"- [{m.level}] {m.logger} : {m.template}" for m in LOG_MESSAGES]
    exemplar_blocks = [
        json.dumps({
            "name": s.name, "question": s.question, "rubric": s.rubric,
            "alert": {"alertname": s.alert.alertname, "severity": s.alert.severity,
                      "fingerprint": s.alert.fingerprint, "summary": s.alert.summary,
                      "description": s.alert.description, "labels": s.alert.labels},
            "logSamples": list(s.log_samples)[:3], "logEnvironment": s.log_environment,
        }, ensure_ascii=False, indent=1)
        for s in exemplars
    ]
    return "\n".join([
        "## 이번에 사용할 알림 (이것만 사용)",
        f"- alertname: {alertname} / severity: {rule.severity}",
        f"- labels는 정확히 이것만 넣는다 (env 같은 라벨 추가 금지): {json.dumps(required_labels, ensure_ascii=False)}",
        f"- summary는 다음 템플릿의 {{}}에 값만 채운 형태여야 한다: {' 또는 '.join(summary_templates)}",
        f"- description도 마찬가지: {' 또는 '.join(description_templates)}",
        "",
        "## 사용 가능한 로그 메시지 카탈로그 ({}는 값 슬롯. 이 목록에 없는 로거/메시지 금지)",
        *message_lines,
        "",
        "## 값 형식 규칙 (슬롯 값도 검증기가 확인한다)",
        "- Outbox 이벤트 id는 숫자다 (예: id=8241). UUID 금지. streamKey는 실제 스트림 키만.",
        "- 정산 recordId는 <ms타임스탬프>-<seq> 형식 (예: 1756172841203-0).",
        "- HTTP uri는 실제 엔드포인트만: /rooms, /rooms/check-joinCode, /rooms/check-guestName, /rooms/nickname/random, /rooms/<대문자숫자4자리>/probabilities, /rooms/<대문자숫자4자리>/settings",
        "- EventDispatcher의 consumer=는 실제 클래스만: RoomJoinConsumer(RoomJoinEvent), SelectCardCommandEventConsumer(SelectCardCommandEvent), PlayerDisconnectedConsumer(PlayerDisconnectedEvent), MiniGameStartConsumer, TapCommandEventConsumer, TouchProgressEventConsumer, StopCommandEventConsumer, LadderDrawCommandEventConsumer",
        "- GameTaskSchedulerFactory의 [게임]과 <게임>-task 스레드의 게임 이름: nunchi, cardgame, racinggame, speedtouch, blindtimer, blockstacking, laddergame",
        "- joinCode는 대문자/숫자 4자리 (예: PXMH).",
        "- 로그 샘플은 반드시 시각 오름차순으로 나열한다.",
        "- 스레드 번호 앞에 하이픈을 넣지 마라: redis-stream-thread-pool-settlement:result1 (O), redis-stream-thread-pool-settlement:result-1 (X)",
        "- question에서 조회 창을 언급하면 반드시 '최근 30분'이다 (시스템의 실제 조회 창).",
        "",
        "## 스레드명 규칙 (로거가 실제로 도는 스레드에만 배치한다)",
        f"- Redis Stream 컨슈머(EventDispatcher, NunchiCommandEventConsumer, SettlementStreamConsumer, RedisStreamListenerStarter): redis-stream-thread-pool-<키><N>. <키>는 다음만 유효: {', '.join(sorted(STREAM_POOL_NAMES))}",
        "- HTTP 요청(RestExceptionHandler, IpBlockFilter/Store): http-nio-8080-exec-<N>",
        "- 스케줄러(OutboxEventProcessor, SettlementPendingSweeper, RedisStreamContainerRecovery, TaskUtils): pool-<N>-thread-<M>",
        "- 게임 스케줄러(GameTaskSchedulerFactory): nunchi-task-1 같은 <게임>-task-<N>",
        "- QR/스토리지(QrCodeService, OracleObjectStorageService): 무명 가상 스레드라 빈 문자열, 즉 '--- []' 형태",
        "",
        "## 기존 골든 시나리오 예시 (형식 참고, 내용 복제 금지)",
        *exemplar_blocks,
        "",
        "## 이번 생성 과제",
        f"- 축: {axis.key} (기대 판정: 근거 발견 {axis.expected})",
        f"- 축 설명: {axis.instruction}",
        f"- 알림: {alertname}",
        f"- 로그 샘플 수: {axis.min_logs}~{axis.max_logs}줄",
        f"- name 뒤에 붙일 일련번호: {ordinal}",
        "- 알림 발생 시각은 2026-08-26 근처의 임의 시각으로 잡고, 로그 시각은 축 설명의 시간 관계를 따른다.",
        "",
        "위 조건으로 시나리오 JSON 하나를 생성하라.",
    ])


class ScenarioGenerator:
    def __init__(self, client: LlmJsonClient):
        self._client = client

    def generate(self, axis: Axis, alertname: str, exemplars: list[Scenario], ordinal: int) -> dict:
        raw = self._client.generate_json(
            SYSTEM_INSTRUCTION, build_prompt(axis, alertname, exemplars, ordinal))
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            parsed = next((item for item in parsed if isinstance(item, dict)), None)
        if not isinstance(parsed, dict):
            raise ValueError(f"생성 응답이 JSON 객체가 아님: {type(parsed).__name__}")
        return parsed
