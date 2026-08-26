"""학습 샘플 검증.

학습 데이터의 정답이 틀리면 틀린 것을 가르친다. 시나리오(입력)는 synthesis.validators가 이미
검증하므로, 여기서는 **정답(교사 출력)이 그 시나리오에 대해 실제로 옳은지**만 본다.

검사는 전부 기계적으로 확인 가능한 것으로 한정한다. "그럴듯한가"는 묻지 않는다.
새 검사는 TargetRule 구현을 추가해 끼운다.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from harness.domain import Analysis, Scenario
from harness.grounding import CitationExistsRule

# 정답 텍스트가 언급했다면 로그나 알림에 실제로 있어야 하는 식별자들.
_IDENTIFIER_PATTERNS = (
    ("스트림 키", re.compile(r"\b(?:stream|streamKey|스트림)\s*[=:]?\s*([a-z]+:[a-z]+|[a-z]{4,})\b")),
    ("컨슈머", re.compile(r"\b([A-Z][A-Za-z]*(?:Consumer|Processor|Sweeper|Service|Handler|Factory))\b")),
    ("joinCode", re.compile(r"\bjoinCode[=:]\s*([A-Z0-9]{4})\b")),
    ("recordId", re.compile(r"\brecordId[=:]\s*(\d{13}-\d+)\b")),
    ("URI", re.compile(r"(/rooms(?:/[A-Za-z0-9-]+)*)")),
)

# 일반 명사와 겹쳐 오탐을 내는 것들은 식별자로 보지 않는다.
_IDENTIFIER_STOPWORDS = frozenset({
    "stream", "streams", "redis", "outbox", "settlement", "error", "errors", "prod",
})


def expects_evidence(scenario: Scenario) -> bool:
    """이 시나리오가 기대하는 근거 판정.

    명시된 expected 필드를 우선한다. rubric 문자열로 추측하면 오답 조건 절에 있는 문구를
    정답으로 잘못 읽는다("아니오로 판정하면 정답. 예로 판정하면 오답"). 실제로 그렇게 틀렸다.
    """
    if scenario.expected:
        return scenario.expected.strip() == "예"
    head = scenario.rubric.split("정답", 1)[0]
    return "근거 발견: 예" in head


class TargetRule(ABC):
    name: str

    @abstractmethod
    def violations(self, scenario: Scenario, target: Analysis) -> list[str]: ...


class VerdictMatchesExpectation(TargetRule):
    """정답의 근거 판정이 시나리오가 기대하는 판정과 같아야 한다."""

    name = "verdict"

    def violations(self, scenario: Scenario, target: Analysis) -> list[str]:
        expected_yes = expects_evidence(scenario)
        if target.evidence_found != expected_yes:
            want = "예" if expected_yes else "아니오"
            got = "예" if target.evidence_found else "아니오"
            return [f"기대 판정 {want}인데 정답은 {got}"]
        return []


class CitationIsVerbatim(TargetRule):
    """근거를 인정한 정답은 로그 원문을 그대로 인용해야 한다.

    소형 모델에게 가르치려는 행동이 바로 이것이므로, 정답 자체가 이걸 어기면 안 된다.
    """

    name = "citation"

    def __init__(self):
        self._rule = CitationExistsRule()

    def violations(self, scenario: Scenario, target: Analysis) -> list[str]:
        if not target.evidence_found:
            return []
        if not target.evidence_line.strip():
            return ["근거를 인정했으나 인용문이 비어 있음"]
        if not self._rule.holds(target, scenario):
            return [f"인용문이 로그에 없음: {target.evidence_line[:60]}"]
        if target.evidence_line.strip() not in scenario.log_samples:
            # 부분 문자열이면 통과하지만, 학습 정답으로는 한 줄 전체를 인용하게 한다.
            return [f"로그 한 줄 전체가 아닌 부분만 인용: {target.evidence_line[:60]}"]
        return []


class NoCauseWithoutEvidence(TargetRule):
    """근거가 없으면 원인을 말하지 않아야 한다."""

    name = "no-cause"

    def violations(self, scenario: Scenario, target: Analysis) -> list[str]:
        if not target.evidence_found and target.root_cause_hypothesis.strip():
            return [f"근거 없음인데 원인 가설이 있음: {target.root_cause_hypothesis[:50]}"]
        return []


class IdentifiersAreGrounded(TargetRule):
    """정답이 언급한 식별자는 로그나 알림에 실제로 존재해야 한다.

    지어낸 스트림 이름이나 컨슈머 이름이 정답에 섞이면 그 환각을 학습하게 된다.
    """

    name = "identifier"

    def violations(self, scenario: Scenario, target: Analysis) -> list[str]:
        haystack = "\n".join(scenario.log_samples)
        haystack += "\n" + scenario.alert.summary + "\n" + scenario.alert.description
        haystack += "\n" + scenario.alert.alertname + "\n" + " ".join(scenario.alert.labels.values())
        text = f"{target.summary}\n{target.root_cause_hypothesis}"
        found = []
        for label, pattern in _IDENTIFIER_PATTERNS:
            for value in pattern.findall(text):
                if value.lower() in _IDENTIFIER_STOPWORDS:
                    continue
                if value not in haystack:
                    found.append(f"{label} '{value}'가 로그와 알림 어디에도 없음")
        return found


class SchemaIsComplete(TargetRule):
    """정답이 비어 있지 않아야 한다."""

    name = "schema"

    def violations(self, scenario: Scenario, target: Analysis) -> list[str]:
        found = []
        if not target.summary.strip():
            found.append("요약이 비어 있음")
        if target.evidence_found and not target.root_cause_hypothesis.strip():
            found.append("근거를 인정했는데 원인 가설이 비어 있음")
        return found


def default_target_rules() -> list[TargetRule]:
    return [
        SchemaIsComplete(),
        VerdictMatchesExpectation(),
        CitationIsVerbatim(),
        NoCauseWithoutEvidence(),
        IdentifiersAreGrounded(),
    ]


def verify_target(scenario: Scenario, target: Analysis,
                  rules: list[TargetRule] | None = None) -> dict[str, list[str]]:
    return {rule.name: rule.violations(scenario, target) for rule in (rules or default_target_rules())}
