"""판정 결과를 의도적으로 훼손해 judge의 변별력을 재는 변형기.

축적된 실측 판정은 97.8%가 PASS라 judge가 오답을 잡아내는 능력을 잴 표본이 없다.
정답으로 판정된 답변을 규칙 위반 방향으로 변형하면, 참조 라벨이 "누가 읽고 매긴 의견"이 아니라
"어떻게 만들었는가"에서 나오므로 사람 라벨링의 주관을 우회할 수 있다.

새 변형은 AnswerMutation 구현을 추가해 끼운다.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

EVIDENCE_YES = "근거 발견: 예"
EVIDENCE_NO = "근거 발견: 아니오"
NO_CAUSE = "원인 가설: (없음)"


@dataclass(frozen=True)
class Probe:
    """judge에게 물어볼 한 건. expected_verdict는 구성 방식이 정한 참조 라벨이다."""

    scenario_name: str
    mutation: str
    answer: str
    expected_verdict: str


@dataclass(frozen=True)
class FlatAnswer:
    """평탄화된 답변의 구조. formatting.AnswerFormatter의 출력 형식을 되읽는다."""

    summary: str
    evidence_found: bool
    cause: str
    actions_block: str

    @classmethod
    def parse(cls, answer: str) -> FlatAnswer | None:
        summary = re.search(r"^요약: (.*)$", answer, re.MULTILINE)
        evidence = re.search(r"^근거 발견: (예|아니오)$", answer, re.MULTILINE)
        cause = re.search(r"^원인 가설: (.*)$", answer, re.MULTILINE)
        actions = re.search(r"^제안 조치:.*$", answer, re.MULTILINE | re.DOTALL)
        if not (summary and evidence and cause and actions):
            return None
        return cls(summary.group(1), evidence.group(1) == "예", cause.group(1), actions.group(0))

    def render(self) -> str:
        evidence = EVIDENCE_YES if self.evidence_found else EVIDENCE_NO
        return f"요약: {self.summary}\n{evidence}\n원인 가설: {self.cause}\n{self.actions_block}"


class AnswerMutation(ABC):
    name: str
    expected_verdict: str

    @abstractmethod
    def apply(self, flat: FlatAnswer) -> FlatAnswer | None:
        """적용할 수 없는 답변이면 None을 돌려준다."""


class Unmutated(AnswerMutation):
    """대조군. 원본 그대로이므로 judge가 PASS해야 한다."""

    name = "unmutated"
    expected_verdict = "PASS"

    def apply(self, flat: FlatAnswer) -> FlatAnswer:
        return flat


class VerdictFlip(AnswerMutation):
    """근거 판정만 뒤집는다. rubric이 요구하는 판정과 정반대가 되므로 FAIL이어야 한다."""

    name = "verdict-flip"
    expected_verdict = "FAIL"

    def apply(self, flat: FlatAnswer) -> FlatAnswer:
        return FlatAnswer(flat.summary, not flat.evidence_found, flat.cause, flat.actions_block)


class FabricatedCause(AnswerMutation):
    """근거 없음 판정에 원인 단정을 끼워 넣는다. 봇이 실제로 저질렀던 오진의 형태다."""

    name = "fabricated-cause"
    expected_verdict = "FAIL"
    CLAIM = "Redis Stream 컨슈머의 처리 지연이 누적되어 발생한 것으로 판단됩니다."

    def apply(self, flat: FlatAnswer) -> FlatAnswer | None:
        if flat.evidence_found:
            return None
        return FlatAnswer(flat.summary, False, self.CLAIM, flat.actions_block)


class ComponentSwap(AnswerMutation):
    """근거는 인정하되 원인을 무관한 컴포넌트로 바꾼다. rubric의 원인 조건을 어기므로 FAIL이어야 한다."""

    name = "component-swap"
    expected_verdict = "FAIL"
    CLAIM = "프론트엔드 정적 파일 캐시 무효화 실패로 인해 발생한 것으로 보입니다."

    def apply(self, flat: FlatAnswer) -> FlatAnswer | None:
        if not flat.evidence_found:
            return None
        return FlatAnswer(flat.summary, True, self.CLAIM, flat.actions_block)


class BenignParaphrase(AnswerMutation):
    """의미를 바꾸지 않고 표현만 손댄다. judge가 표면 표현에 과민한지 재는 대조군이라 PASS여야 한다."""

    name = "benign-paraphrase"
    expected_verdict = "PASS"

    def apply(self, flat: FlatAnswer) -> FlatAnswer:
        return FlatAnswer(f"확인 결과, {flat.summary}", flat.evidence_found, flat.cause, flat.actions_block)


DEFAULT_MUTATIONS: tuple[AnswerMutation, ...] = (
    Unmutated(), VerdictFlip(), FabricatedCause(), ComponentSwap(), BenignParaphrase())


def build_probes(scenario_name: str, answer: str,
                 mutations: tuple[AnswerMutation, ...] = DEFAULT_MUTATIONS) -> list[Probe]:
    flat = FlatAnswer.parse(answer)
    if flat is None:
        return []
    probes = []
    for mutation in mutations:
        mutated = mutation.apply(flat)
        if mutated is None:
            continue
        probes.append(Probe(scenario_name, mutation.name, mutated.render(), mutation.expected_verdict))
    return probes
