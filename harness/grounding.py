"""접지 검증. 모델의 근거 주장을 코드로 확인하고, 통과하지 못하면 강등한다.

새 검증(타임스탬프 창 검사, 표본 수 검사 등)은 GroundingRule 구현을 추가해 파이프라인에
끼우면 되고, 기존 규칙과 호출부는 수정하지 않는다. RLVR 단계의 보상 함수도 이 규칙들을 재사용한다.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import replace

from harness.domain import Analysis, Scenario

# 자바 GeminiAnomalyAnalyzer.NO_EVIDENCE_SUMMARY와 동일해야 한다.
NO_EVIDENCE_SUMMARY = "제공된 로그에서 이 알림을 뒷받침할 근거를 찾지 못했습니다."

_WHITESPACE = re.compile(r"\s+")


def _normalize_whitespace(text: str) -> str:
    return _WHITESPACE.sub(" ", text.strip())


class GroundingRule(ABC):
    """분석 하나에 대해 '근거로 인정할 수 있는가'를 판정한다."""

    @abstractmethod
    def holds(self, analysis: Analysis, scenario: Scenario) -> bool: ...


class CitationExistsRule(GroundingRule):
    """자바 citedInLogs와 동일: 인용 줄이 공백 정규화 후 실제 로그 샘플에 부분 문자열로 존재해야 한다."""

    def holds(self, analysis: Analysis, scenario: Scenario) -> bool:
        needle = _normalize_whitespace(analysis.evidence_line)
        if not needle:
            return False
        return any(needle in _normalize_whitespace(line) for line in scenario.log_samples)


class GroundingPipeline:
    """모든 규칙을 통과할 때만 grounded=True. 하나라도 어기면 자바 parse와 동일하게
    요약을 표준 문구로, 가설을 빈 문자열로 강등한다."""

    def __init__(self, rules: list[GroundingRule] | None = None):
        self._rules = rules if rules is not None else [CitationExistsRule()]

    def apply(self, analysis: Analysis, scenario: Scenario) -> Analysis:
        grounded = analysis.evidence_found and all(
            rule.holds(analysis, scenario) for rule in self._rules)
        if grounded:
            return replace(analysis, grounded=True)
        return replace(
            analysis, grounded=False, summary=NO_EVIDENCE_SUMMARY, root_cause_hypothesis="")
