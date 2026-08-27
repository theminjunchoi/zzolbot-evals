"""검증 가능한 보상 함수.

하나의 함수가 세 역할을 겸한다.
- 학습 신호: RFT가 샘플을 고르는 기준, DPO가 선호 쌍을 만드는 기준
- 평가 종점: judge를 부르지 않으므로 API 비용이 0이고 채점 변동이 섞이지 않는다
- 판정 기준: 사전 등록한 성공 조건을 이 값으로 판정한다

이진 PASS로 세면 정보를 버려 검정력이 없다(33종에서 3건 개선은 p=0.25). 연속값이면
짝지은 비모수 검정을 쓸 수 있어 같은 표본으로 중간 크기 효과를 잡는다.

배점은 `RewardSpec`으로 분리해, 항목을 빼거나 가중치를 바꿔도 호출부가 그대로다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from harness.domain import Analysis, Scenario
from training.verification import (
    CitationIsVerbatim,
    NoCauseWithoutEvidence,
    SchemaIsComplete,
    expects_evidence,
)

# 원인 문장이 지목했는지 확인할 식별자. 인용한 로그 줄에서 뽑는다.
# training.verification._IDENTIFIER_PATTERNS는 "정답이 언급한 것이 로그에 있는가"를 보는
# 반대 방향이라 그대로 쓸 수 없다. 여기서는 로그 줄에서 이름을 뽑아낸다.
_LOGGER = re.compile(r"---\s*\[[^\]]*\]\s*(\S+)\s*:")
_THREAD = re.compile(r"---\s*\[([^\]]*)\]")
_CLASS_IN_MESSAGE = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Consumer|Processor|Worker|Sweeper|Service"
                               r"|Handler|Factory|Manager|Starter|Recovery|Dispatcher|Filter|Store))\b")
_STREAM_IN_THREAD = re.compile(r"redis-stream-thread-pool-([a-z:]+?)\d*$")
_STREAM_KV = re.compile(r"streamKey[=:]\s*([a-z:]+)")


def evidence_identifiers(line: str) -> set[str]:
    """로그 한 줄이 지목하는 이름들. 원인 문장이 이 중 하나를 말해야 구체적이라고 본다."""
    names: set[str] = set()
    logger = _LOGGER.search(line)
    if logger:
        full = logger.group(1)
        names.add(full)
        names.add(full.rsplit(".", 1)[-1])  # c.g.o.OutboxEventProcessor -> OutboxEventProcessor
    names.update(_CLASS_IN_MESSAGE.findall(line))
    names.update(_STREAM_KV.findall(line))
    for thread in _THREAD.findall(line):
        stream = _STREAM_IN_THREAD.match(thread.strip())
        if stream:
            names.add(stream.group(1))
    return {n for n in names if len(n) >= 4}


class CauseNamesEvidenceComponent:
    """원인 가설이 근거 줄에 등장하는 이름을 최소 하나 지목해야 한다.

    지금까지 원인 구체성은 judge만 판정할 수 있어 학습 표적으로 삼지 못했다. 이 규칙이
    그것을 코드로 옮긴다. 판정이 judge와 얼마나 맞는지는 배점에 넣기 전에 실측한다.
    """

    name = "cause-specificity"

    def holds(self, scenario: Scenario, target: Analysis) -> bool:
        if not expects_evidence(scenario):
            return True  # 근거 없음이 정답이면 원인을 말하지 않는 것이 맞다
        cause = target.root_cause_hypothesis or ""
        if not cause.strip():
            return False
        names = evidence_identifiers(target.evidence_line or "")
        if not names:
            return False
        return any(n in cause for n in names)


@dataclass(frozen=True)
class RewardSpec:
    """배점. 항목을 빼려면 가중치를 0으로 두면 되고 호출부는 바뀌지 않는다.

    specificity는 기본 0이다. 사전 등록한 검사(judge 판정과의 일치율 60% 이상)를
    통과하지 못했다. 실측 38%였고, 어긋난 131건 중 123건이 **규칙이 judge보다 엄격한**
    방향이었다. judge는 클래스 이름이 아니라 메커니즘을 한국어로 짚어도 구체적이라고 본다.

        원인: "Oracle Object Storage 서비스와의 통신 문제로 읽기 시간 초과"  → judge 통과
        로그의 이름: OracleObjectStorageService, QrCodeService              → 규칙 탈락

    타당한 원인 서술인데 이름 일치를 요구해 떨어뜨린 것이다. 조작적 정의가 틀렸다.
    같은 데이터에 맞춰 규칙을 고치면 맞추기가 되므로 지금은 배점에서 빼고, 규칙 자체는
    진단용으로 남긴다. 다시 설계할 때는 이 데이터가 아닌 곳에서 검증한다.
    """

    schema: float = 0.10
    verdict: float = 0.50
    citation: float = 0.40
    specificity: float = 0.0
    cause_without_evidence_penalty: float = 0.30


@dataclass(frozen=True)
class RewardBreakdown:
    """총점과 항목별 획득. 어디서 점수를 잃었는지 봐야 진단이 된다."""

    total: float
    parts: dict[str, float] = field(default_factory=dict)
    parse_failed: bool = False

    @property
    def clamped(self) -> float:
        return max(0.0, min(1.0, self.total))


class RewardFunction:
    """분석 하나를 0.0 ~ 1.0으로 채점한다.

    근거 없음이 정답인 시나리오에서는 인용과 구체성을 만점 처리한다. 그러지 않으면 음성
    시나리오의 상한이 0.5가 되어 양성과 척도가 어긋나고, 음성만 잘하는 모델이 낮게 나온다.
    """

    def __init__(self, spec: RewardSpec | None = None):
        self._spec = spec or RewardSpec()
        self._schema = SchemaIsComplete()
        self._citation = CitationIsVerbatim()
        self._no_cause = NoCauseWithoutEvidence()
        self._specificity = CauseNamesEvidenceComponent()

    def score(self, scenario: Scenario, target: Analysis | None) -> RewardBreakdown:
        spec = self._spec
        if target is None:  # 파싱 실패. 형식 점수조차 못 받는다
            return RewardBreakdown(0.0, {"schema": 0.0}, parse_failed=True)

        parts: dict[str, float] = {}
        parts["schema"] = spec.schema if not self._schema.violations(scenario, target) else 0.0

        expects_yes = expects_evidence(scenario)
        parts["verdict"] = spec.verdict if target.evidence_found == expects_yes else 0.0

        if expects_yes:
            ok = not self._citation.violations(scenario, target)
            parts["citation"] = spec.citation if ok else 0.0
            parts["specificity"] = spec.specificity if self._specificity.holds(scenario, target) else 0.0
        else:
            # 해당 없음. 만점 처리해 양성과 척도를 맞춘다.
            parts["citation"] = spec.citation
            parts["specificity"] = spec.specificity

        penalty = 0.0
        if self._no_cause.violations(scenario, target):
            penalty = spec.cause_without_evidence_penalty
        parts["penalty"] = -penalty

        return RewardBreakdown(sum(parts.values()), parts)
