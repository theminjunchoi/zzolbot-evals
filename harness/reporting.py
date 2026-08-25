"""결과 기록과 집계. 새 출력 형식은 ResultSink 구현을 추가해 확장한다."""

from __future__ import annotations

import dataclasses
import json
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path

from harness.domain import TrialResult


class ResultSink(ABC):
    @abstractmethod
    def write(self, result: TrialResult) -> None: ...


class JsonlSink(ResultSink):
    """시행 1건을 JSONL 한 줄로 즉시 기록한다. 중간에 끊겨도 그때까지의 결과가 남는다."""

    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, result: TrialResult) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dataclasses.asdict(result), ensure_ascii=False) + "\n")


@dataclasses.dataclass(frozen=True)
class ScenarioStats:
    name: str
    trials: int
    passes: int
    mean_accuracy: float
    mean_groundedness: float
    hallucinations: int
    errors: int

    @property
    def pass_rate(self) -> float:
        return self.passes / self.trials if self.trials else 0.0


class ReportBuilder:

    def aggregate(self, results: list[TrialResult]) -> list[ScenarioStats]:
        grouped: dict[str, list[TrialResult]] = defaultdict(list)
        for result in results:
            grouped[result.scenario_name].append(result)
        stats = []
        for name in sorted(grouped):
            rows = grouped[name]
            stats.append(ScenarioStats(
                name=name,
                trials=len(rows),
                passes=sum(1 for r in rows if r.score.passed),
                mean_accuracy=sum(r.score.accuracy for r in rows) / len(rows),
                mean_groundedness=sum(r.score.groundedness for r in rows) / len(rows),
                hallucinations=sum(1 for r in rows if r.score.hallucination_detected),
                errors=sum(1 for r in rows if r.error),
            ))
        return stats

    def to_markdown(self, label: str, model: str, stats: list[ScenarioStats]) -> str:
        total_trials = sum(s.trials for s in stats)
        total_passes = sum(s.passes for s in stats)
        perfect = sum(1 for s in stats if s.passes == s.trials)
        lines = [
            f"# 평가 리포트: {label}",
            "",
            f"- 모델: {model}",
            f"- 시나리오 {len(stats)}종, 시행 {total_trials}건 (시행은 독립, 조기 중단 없음)",
            f"- 시행 PASS율: {total_passes}/{total_trials}"
            f" ({100.0 * total_passes / total_trials:.1f}%)" if total_trials else "- 시행 없음",
            f"- 전 시행 PASS 시나리오: {perfect}/{len(stats)}",
            "",
            "| 시나리오 | PASS | acc 평균 | grd 평균 | 환각 | 오류 |",
            "|---|---|---|---|---|---|",
        ]
        for s in stats:
            lines.append(
                f"| {s.name} | {s.passes}/{s.trials} | {s.mean_accuracy:.1f} "
                f"| {s.mean_groundedness:.1f} | {s.hallucinations} | {s.errors} |")
        return "\n".join(lines) + "\n"
