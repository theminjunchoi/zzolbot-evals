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

    def applies_to(self, rubric: str) -> bool:
        """채점 기준에 따라 참조 라벨이 성립하지 않는 변형은 여기서 걸러낸다."""
        return True


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


class VagueCause(AnswerMutation):
    """원인을 구체 컴포넌트 없이 뭉뚱그린다. 판정은 맞지만 rubric이 요구하는 원인 특정에
    미달하는 경계 사례다. judge가 이걸 통과시키면 채점이 느슨한 것이다."""

    name = "vague-cause"
    expected_verdict = "FAIL"
    CLAIM = "시스템 내부의 일시적인 문제로 인해 발생한 것으로 보입니다."

    def apply(self, flat: FlatAnswer) -> FlatAnswer | None:
        if not flat.evidence_found:
            return None
        return FlatAnswer(flat.summary, True, self.CLAIM, flat.actions_block)


class HedgedVerdict(AnswerMutation):
    """판정 라벨은 유지하되 요약에서 확신을 흐린다. 계약 문자열은 그대로이므로 rubric의
    판정 조건은 충족한다. judge가 표현의 머뭇거림만으로 떨어뜨리면 과민한 것이다."""

    name = "hedged-summary"
    expected_verdict = "PASS"

    def apply(self, flat: FlatAnswer) -> FlatAnswer:
        summary = f"{flat.summary} 다만 추가 확인이 필요할 수 있습니다."
        return FlatAnswer(summary, flat.evidence_found, flat.cause, flat.actions_block)


class TruncatedActions(AnswerMutation):
    """제안 조치를 비운다. 판정과 원인만 요구하는 채점 기준이라면 통과해야 하므로,
    judge가 기준에 없는 요소를 요구하는지 재는 대조군이 된다.

    다만 채점 기준이 특정 사실의 "언급"이나 "명시"를 요구하는 경우, 그 서술이 제안 조치에만
    담겨 있을 수 있다. 그때 조치를 비우면 답변이 실제로 기준을 어기게 되어 PASS 기대가
    성립하지 않는다. 실측에서 이 경우를 과잉 탈락으로 잘못 집계한 적이 있어 걸러낸다."""

    name = "no-actions"
    expected_verdict = "PASS"
    _MENTION_REQUIRED = ("언급", "명시")

    def apply(self, flat: FlatAnswer) -> FlatAnswer:
        return FlatAnswer(flat.summary, flat.evidence_found, flat.cause, "제안 조치: (없음)")

    def applies_to(self, rubric: str) -> bool:
        return not any(word in rubric for word in self._MENTION_REQUIRED)


# 명백한 오답을 다루는 1차 프로브. judge의 하한을 잰다.
GROSS_MUTATIONS: tuple[AnswerMutation, ...] = (
    Unmutated(), VerdictFlip(), FabricatedCause(), ComponentSwap(), BenignParaphrase())

# 경계 영역 프로브. 실측에서 관찰된 판정 변동(같은 답변에 acc 3→5→3)이 일어나는 구간을 겨냥한다.
SUBTLE_MUTATIONS: tuple[AnswerMutation, ...] = (
    VagueCause(), HedgedVerdict(), TruncatedActions())

DEFAULT_MUTATIONS: tuple[AnswerMutation, ...] = GROSS_MUTATIONS + SUBTLE_MUTATIONS

MUTATION_SETS: dict[str, tuple[AnswerMutation, ...]] = {
    "gross": GROSS_MUTATIONS,
    "subtle": SUBTLE_MUTATIONS,
    "all": DEFAULT_MUTATIONS,
}


def build_probes(scenario_name: str, answer: str,
                 mutations: tuple[AnswerMutation, ...] = DEFAULT_MUTATIONS,
                 rubric: str = "") -> list[Probe]:
    flat = FlatAnswer.parse(answer)
    if flat is None:
        return []
    probes = []
    for mutation in mutations:
        if not mutation.applies_to(rubric):
            continue
        mutated = mutation.apply(flat)
        if mutated is None:
            continue
        probes.append(Probe(scenario_name, mutation.name, mutated.render(), mutation.expected_verdict))
    return probes
