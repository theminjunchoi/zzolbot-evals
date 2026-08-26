"""사전 등록한 두 종점을 judge 없이 재는 계산.

2회전의 판정 조건은 인용 통과와 오탐 두 가지뿐이고, 둘 다 코드로 확인 가능하다.
judge를 거치지 않으므로 API 비용이 들지 않고 judge 변동성도 섞이지 않는다.

- 인용 통과: 근거가 있는 시나리오에서 모델이 근거를 주장하고, 그 인용이 로그 원문에 실제로 있는가
- 오탐: 근거가 없는 시나리오인데 모델이 근거를 주장하고 접지까지 통과했는가
"""

from __future__ import annotations

from dataclasses import dataclass

from harness.analyzer import PromptedAnalyzer
from harness.domain import Scenario
from harness.grounding import GroundingPipeline
from training.verification import expects_evidence


@dataclass(frozen=True)
class ScenarioOutcome:
    name: str
    expects_yes: bool
    claimed: bool
    grounded: bool
    parse_failed: bool


@dataclass(frozen=True)
class EndpointReport:
    label: str
    outcomes: tuple[ScenarioOutcome, ...]

    @property
    def positives(self) -> tuple[ScenarioOutcome, ...]:
        return tuple(o for o in self.outcomes if o.expects_yes)

    @property
    def negatives(self) -> tuple[ScenarioOutcome, ...]:
        return tuple(o for o in self.outcomes if not o.expects_yes)

    @property
    def citation_pass(self) -> int:
        return sum(1 for o in self.positives if o.grounded)

    @property
    def claimed_on_positives(self) -> int:
        return sum(1 for o in self.positives if o.claimed)

    @property
    def false_positives(self) -> int:
        return sum(1 for o in self.negatives if o.grounded)

    @property
    def parse_failures(self) -> int:
        return sum(1 for o in self.outcomes if o.parse_failed)

    def as_dict(self) -> dict[str, bool]:
        return {o.name: o.grounded for o in self.outcomes}


class EndpointRunner:
    """분석기 하나를 시나리오 전부에 돌려 종점 지표를 만든다."""

    def __init__(self, analyzer: PromptedAnalyzer, grounding: GroundingPipeline | None = None):
        self._analyzer = analyzer
        self._grounding = grounding or GroundingPipeline()

    def run(self, label: str, scenarios: list[Scenario]) -> EndpointReport:
        outcomes = []
        for scenario in scenarios:
            expects_yes = expects_evidence(scenario)
            try:
                analysis = self._analyzer.analyze(scenario)
            except Exception:  # noqa: BLE001 - 파싱 실패도 결과의 일부다
                outcomes.append(ScenarioOutcome(scenario.name, expects_yes, False, False, True))
                continue
            settled = self._grounding.apply(analysis, scenario)
            outcomes.append(ScenarioOutcome(
                scenario.name, expects_yes, analysis.evidence_found, settled.grounded, False))
        return EndpointReport(label, tuple(outcomes))


def paired_counts(before: EndpointReport, after: EndpointReport,
                  only_positives: bool) -> tuple[int, int, int]:
    """짝지은 비교의 (개선, 악화, 동일). 음성 집합에서는 접지 통과가 곧 오탐이라 방향이 뒤집힌다."""
    lhs = {o.name: o for o in (before.positives if only_positives else before.negatives)}
    rhs = {o.name: o for o in (after.positives if only_positives else after.negatives)}
    better = worse = same = 0
    for name, b in lhs.items():
        a = rhs.get(name)
        if a is None or a.grounded == b.grounded:
            same += 1
            continue
        gained = a.grounded and not b.grounded
        if gained is only_positives:
            better += 1
        else:
            worse += 1
    return better, worse, same


def two_sided_binomial(better: int, worse: int) -> float:
    """짝지은 이항검정(McNemar 정확검정)의 양측 p값."""
    from math import comb

    n = better + worse
    if n == 0:
        return 1.0
    k = min(better, worse)
    tail = sum(comb(n, i) for i in range(0, k + 1))
    return min(1.0, 2.0 * tail / (2 ** n))
