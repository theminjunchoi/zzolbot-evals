"""judge 변별력 측정. 프로브를 judge에 태우고 참조 라벨과의 일치율을 집계한다."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from analysis.mutations import Probe
from harness.domain import Scenario
from harness.judge import Judge


@dataclass(frozen=True)
class ProbeResult:
    probe: Probe
    judge_verdict: str
    rationale: str

    @property
    def agreed(self) -> bool:
        return self.judge_verdict == self.probe.expected_verdict

    @property
    def missed(self) -> bool:
        """오답이어야 하는데 judge가 통과시킨 경우."""
        return self.probe.expected_verdict == "FAIL" and self.judge_verdict == "PASS"

    @property
    def over_strict(self) -> bool:
        """정답이어야 하는데 judge가 떨어뜨린 경우."""
        return self.probe.expected_verdict == "PASS" and self.judge_verdict == "FAIL"


class CalibrationRunner:
    def __init__(self, judge: Judge, on_result: Callable[[ProbeResult], None] | None = None):
        self._judge = judge
        self._on_result = on_result or (lambda result: None)

    def run(self, scenarios: dict[str, Scenario], probes: list[Probe]) -> list[ProbeResult]:
        results = []
        for probe in probes:
            scenario = scenarios[probe.scenario_name]
            score = self._judge.evaluate(scenario.question, scenario.rubric, probe.answer)
            result = ProbeResult(probe, score.verdict, score.rationale)
            results.append(result)
            self._on_result(result)
        return results


@dataclass(frozen=True)
class MutationStats:
    mutation: str
    expected_verdict: str
    total: int
    agreed: int

    @property
    def agreement(self) -> float:
        return self.agreed / self.total if self.total else 0.0


class CalibrationReport:

    def by_mutation(self, results: list[ProbeResult]) -> list[MutationStats]:
        grouped: dict[str, list[ProbeResult]] = defaultdict(list)
        for result in results:
            grouped[result.probe.mutation].append(result)
        stats = []
        for mutation in sorted(grouped):
            rows = grouped[mutation]
            stats.append(MutationStats(
                mutation=mutation,
                expected_verdict=rows[0].probe.expected_verdict,
                total=len(rows),
                agreed=sum(1 for r in rows if r.agreed),
            ))
        return stats

    def to_markdown(self, label: str, model: str, results: list[ProbeResult]) -> str:
        total = len(results)
        agreed = sum(1 for r in results if r.agreed)
        missed = [r for r in results if r.missed]
        over_strict = [r for r in results if r.over_strict]
        lines = [
            f"# judge 캘리브레이션: {label}",
            "",
            f"- judge 모델: {model}",
            f"- 프로브 {total}건 (참조 라벨은 변형 방식이 결정한다)",
            f"- 전체 일치율: {agreed}/{total} ({100.0 * agreed / total:.1f}%)" if total else "- 프로브 없음",
            f"- 놓친 오답(FAIL이어야 하는데 PASS): {len(missed)}건",
            f"- 과잉 탈락(PASS여야 하는데 FAIL): {len(over_strict)}건",
            "",
            "| 변형 | 참조 라벨 | 일치 | 일치율 |",
            "|---|---|---|---|",
        ]
        for stats in self.by_mutation(results):
            lines.append(
                f"| {stats.mutation} | {stats.expected_verdict} | {stats.agreed}/{stats.total} "
                f"| {100.0 * stats.agreement:.0f}% |")
        if missed:
            lines.extend(["", "## 놓친 오답", ""])
            for r in missed:
                lines.append(f"- `{r.probe.scenario_name}` [{r.probe.mutation}] {r.rationale[:160]}")
        if over_strict:
            lines.extend(["", "## 과잉 탈락", ""])
            for r in over_strict:
                lines.append(f"- `{r.probe.scenario_name}` [{r.probe.mutation}] {r.rationale[:160]}")
        return "\n".join(lines) + "\n"
