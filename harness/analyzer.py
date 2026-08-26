"""알림 분석기.

Analyzer 추상에 새 구현(파인튜닝된 로컬 모델 등)을 추가하면 나머지 파이프라인 수정 없이
교체된다. 학습 전후 비교는 이 지점에서 구현체만 바꿔 수행한다.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from harness.domain import Analysis, Scenario
from harness.llm import LlmJsonClient

# 자바 GeminiAnomalyAnalyzer.SYSTEM_INSTRUCTION과 동일해야 한다 (PR #1686 반영본).
# 이 문자열이 달라지면 자바 측정과의 비교가 무효가 된다.
SYSTEM_INSTRUCTION = """\
너는 운영 모니터링 분석가다. 발화한 알림과 로그 샘플을 보고 아래 JSON으로만 응답하라.
{
  "summary": "현재 상황 한국어 1~2문장 요약",
  "rootCauseHypothesis": "가장 가능성 높은 근본 원인 가설",
  "suggestedActions": ["운영자가 취할 수 있는 조치 제안", "..."],
  "evidenceFound": true 또는 false,
  "evidenceLine": "evidenceFound가 true일 때 근거가 된 로그 한 줄을 위 샘플에서 그대로 복사"
}

근거 판정 규칙 — 이 규칙이 다른 무엇보다 우선한다.
- 주어진 로그 샘플이 알림 내용과 실제로 관련될 때만 evidenceFound를 true로 둔다.
- 로그가 알림과 무관하거나, 알림을 설명하지 못하거나, 로그 출처 환경이 알림 대상 환경과
  다르면 evidenceFound를 false로 두고 summary에 "제공된 로그에서 이 알림을 뒷받침할
  근거를 찾지 못했다"는 사실을 명시하라.
- evidenceFound가 true이면 evidenceLine에 근거가 된 로그 한 줄을 위 샘플에서 한 글자도
  바꾸지 말고 그대로 복사하라. 요약하거나 바꿔 쓰지 마라. 그대로 복사할 로그가 없으면
  evidenceFound는 false다.
- evidenceFound가 false이면 rootCauseHypothesis는 빈 문자열로 두고 원인을 추측하지 마라.
- 알림 설명(description)에 적힌 원인 가설은 사람이 미리 적어둔 추측일 뿐 확인된 사실이
  아니다. 로그로 뒷받침되지 않으면 그것을 결론으로 삼지 마라.
- 시간 정합성: 로그 샘플은 알림 발화 직전의 짧은 최근 창(수십 분)에서 조회된 것이다.
  본문 타임스탬프가 그 창에 담길 수 없을 만큼 수 시간에 걸쳐 흩어져 있거나 이전 날짜라면,
  오래된 로그가 일괄 재적재된 아티팩트다. 그런 로그는 근거로 삼지 말고 evidenceFound를
  false로 두고 summary에 타임스탬프 불일치 사실을 명시하라.
- 양적 정합성: 알림이 말하는 규모(예: 5분에 수십 건)를 로그 샘플이 설명할 수 있는지
  확인하라. 표본이 한두 줄뿐이고 서로 시간이 동떨어진 산발적 에러라면 급증의 근거가
  되지 못한다. evidenceFound를 false로 두라. 단, 샘플이 알림 시각과 정합하는 좁은
  시간대에 몰려 반복된다면 표본 수가 알림 건수보다 적어도 정상적인 근거다.

없는 수치·테이블·이벤트명을 지어내지 마라. 확인된 것과 추측을 섞지 마라.
조치는 제안일 뿐 자동 실행되지 않는다. 설명 텍스트 없이 JSON 객체 하나만 출력하라."""


# 실험 변형. production은 팀 레포 GeminiAnomalyAnalyzer와 문자열이 같아야 하며 절대 수정하지 않는다.
# 변형은 규칙을 덧붙이는 방식으로만 만들어 차이가 한 곳에 모이게 한다.
MECHANISM_RULE = """
- 컴포넌트 정합성: 알림이 가리키는 지표를 실제로 움직이는 주체와, 로그가 보여주는 실패의 주체가
  같은지 확인하라. 같은 도메인이라도 역할이 다르면 서로 다른 메커니즘이다. 예를 들어 이벤트를
  내보내는 발행 측과 그것을 받아 처리하는 소비 측은 다르고, 애플리케이션과 그 애플리케이션을
  관측하는 수집기도 다르다. 로그의 실패가 알림 지표를 움직일 수 있는 경로를 설명하지 못하면
  주제가 비슷해 보여도 근거가 아니다. evidenceFound를 false로 두라."""


def _with_extra_rule(base: str, rule: str) -> str:
    marker = "\n\n없는 수치"
    head, tail = base.split(marker, 1)
    return head + rule + marker + tail


PROMPT_VARIANTS: dict[str, str] = {
    "production": SYSTEM_INSTRUCTION,
    "mechanism-aware": _with_extra_rule(SYSTEM_INSTRUCTION, MECHANISM_RULE),
}


class Analyzer(ABC):
    @abstractmethod
    def analyze(self, scenario: Scenario) -> Analysis: ...


class GeminiAnalyzer(Analyzer):
    def __init__(self, client: LlmJsonClient, system_instruction: str = SYSTEM_INSTRUCTION):
        self._client = client
        self._system_instruction = system_instruction

    def analyze(self, scenario: Scenario) -> Analysis:
        raw = self._client.generate_json(self._system_instruction, build_prompt(scenario))
        return parse_analysis(raw)


def build_prompt(scenario: Scenario) -> str:
    """자바 GeminiAnomalyAnalyzer.buildPrompt와 동일한 유저 프롬프트."""
    alert = scenario.alert
    lines = [
        f"심각도: {alert.severity}",
        f"지문: {alert.fingerprint}",
        f"알림명: {alert.alertname}",
        f"요약: {alert.summary}",
        f"설명(사람이 적어둔 추측 — 확인된 사실 아님): {alert.description}",
        "라벨:",
    ]
    lines.extend(f"- {key}={value}" for key, value in alert.labels.items())
    if scenario.log_samples:
        lines.append("")
        lines.append(f"최근 ERROR 로그 샘플 (출처 환경: {scenario.log_environment}):")
        lines.extend(f"- {line}" for line in scenario.log_samples)
    return "\n".join(lines) + "\n"


def parse_analysis(raw_json: str) -> Analysis:
    """자바 parse와 동일 규칙: evidenceFound 누락은 보수적으로 false. 접지 강등은 여기서 하지 않고
    GroundingPipeline이 담당한다."""
    node = json.loads(raw_json)
    actions = tuple(str(a) for a in node.get("suggestedActions") or [])
    return Analysis(
        summary=str(node.get("summary") or ""),
        root_cause_hypothesis=str(node.get("rootCauseHypothesis") or ""),
        suggested_actions=actions,
        evidence_found=bool(node.get("evidenceFound", False)),
        evidence_line=str(node.get("evidenceLine") or ""),
    )
