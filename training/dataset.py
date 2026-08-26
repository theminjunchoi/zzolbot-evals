"""교사 출력을 학습 샘플로 만든다.

정답은 검증을 통과한 것만 채택한다. 인용이 로그의 부분 문자열일 때는 그 줄 전체로 복원하는데,
이건 내용을 지어내는 것이 아니라 이미 로그에 있는 문자열로 되돌리는 것이고, 소형 모델에게
가르치려는 행동(한 줄 전체를 그대로 인용)과도 일치한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

from harness.analyzer import SYSTEM_INSTRUCTION, build_prompt
from harness.domain import Analysis, Scenario


@dataclass(frozen=True)
class TrainingSample:
    scenario_name: str
    system: str
    user: str
    assistant: str

    def to_chat(self) -> dict:
        return {"messages": [
            {"role": "system", "content": self.system},
            {"role": "user", "content": self.user},
            {"role": "assistant", "content": self.assistant},
        ]}


def repair_citation(analysis: Analysis, scenario: Scenario) -> Analysis:
    """인용이 어느 로그 한 줄의 부분 문자열이면 그 줄 전체로 되돌린다.

    두 줄 이상에 걸치거나 어디에도 없으면 손대지 않는다. 그 경우는 검증에서 걸러진다.
    """
    needle = analysis.evidence_line.strip()
    if not needle or needle in scenario.log_samples:
        return analysis
    matches = [line for line in scenario.log_samples if needle in line]
    if len(matches) != 1:
        return analysis
    return replace(analysis, evidence_line=matches[0])


def to_target_json(analysis: Analysis) -> str:
    """분석기가 기대하는 응답 스키마 그대로. 학습 목표 문자열이 된다."""
    return json.dumps({
        "summary": analysis.summary,
        "rootCauseHypothesis": analysis.root_cause_hypothesis,
        "suggestedActions": list(analysis.suggested_actions),
        "evidenceFound": analysis.evidence_found,
        "evidenceLine": analysis.evidence_line,
    }, ensure_ascii=False)


def build_sample(scenario: Scenario, analysis: Analysis) -> TrainingSample:
    return TrainingSample(
        scenario_name=scenario.name,
        system=SYSTEM_INSTRUCTION,
        user=build_prompt(scenario),
        assistant=to_target_json(analysis),
    )
