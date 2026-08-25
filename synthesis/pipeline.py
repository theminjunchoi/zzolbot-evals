"""합성 파이프라인: 생성 → rule 필터 → 생존 후보 저장 + 탈락 통계 리포트.

생존 후보는 golden-set에 바로 넣지 않고 candidates/에 둔다. 사람 검토(정확성 최종 확인)를
거쳐 승격하는 것이 원칙이다. expected/axis 메타 필드는 승격 시 제거한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.domain import Scenario
from synthesis.axes import Axis
from synthesis.generator import ScenarioGenerator
from synthesis.validators import FilterStats, default_validators, validate


@dataclass(frozen=True)
class BatchItem:
    axis: Axis
    alertname: str
    count: int


class SynthesisPipeline:
    def __init__(self, generator: ScenarioGenerator, exemplars: list[Scenario],
                 existing_names: set[str], out_dir: Path):
        self._generator = generator
        self._exemplars = exemplars
        self._existing_names = set(existing_names)
        self._out_dir = out_dir
        self.stats = FilterStats()

    def run(self, batch: list[BatchItem], on_progress=print) -> list[Path]:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        ordinal = 1
        for item in batch:
            exemplars = self._pick_exemplars(item.axis)
            for _ in range(item.count):
                saved_path = self._one(item, exemplars, ordinal, on_progress)
                if saved_path:
                    saved.append(saved_path)
                ordinal += 1
        return saved

    def _one(self, item: BatchItem, exemplars: list[Scenario], ordinal: int, on_progress) -> Path | None:
        try:
            candidate = self._generator.generate(item.axis, item.alertname, exemplars, ordinal)
        except Exception as e:  # noqa: BLE001 - 생성 실패도 통계에 남긴다
            self.stats.record(f"(생성 실패 #{ordinal})", {"generation": [str(e)]})
            on_progress(f"[DROP] 생성 실패 #{ordinal}: {str(e)[:80]}")
            return None
        candidate.setdefault("axis", item.axis.key)
        candidate.setdefault("expected", item.axis.expected)
        failures = validate(candidate, default_validators(self._existing_names))
        name = candidate.get("name", f"(이름 없음 #{ordinal})")
        if not self.stats.record(name, failures):
            reasons = [r for rs in failures.values() for r in rs]
            on_progress(f"[DROP] {name}: {reasons[0]}" + (f" 외 {len(reasons) - 1}건" if len(reasons) > 1 else ""))
            return None
        self._existing_names.add(name)
        path = self._out_dir / f"{name}.json"
        path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        on_progress(f"[KEEP] {name} ({item.axis.key}, {item.alertname})")
        return path

    def _pick_exemplars(self, axis: Axis) -> list[Scenario]:
        matching = [s for s in self._exemplars
                    if ("근거 발견: 예" in s.rubric) == (axis.expected == "예")]
        return (matching or self._exemplars)[:2]

    def stats_markdown(self) -> str:
        s = self.stats
        lines = [
            "## 합성 필터 통계",
            "",
            f"- 생성 시도: {s.total}건, 생존: {s.passed}건 "
            f"({100.0 * s.passed / s.total:.0f}%)" if s.total else "- 시도 없음",
            "",
            "| 검증기 | 탈락 건수 |",
            "|---|---|",
        ]
        for validator_name, count in s.dropped_by.most_common():
            lines.append(f"| {validator_name} | {count} |")
        lines.extend(["", "### 탈락 사유 상세", ""])
        for name, validator_name, reasons in s.reasons:
            lines.append(f"- `{name}` [{validator_name}] {'; '.join(reasons)[:200]}")
        return "\n".join(lines) + "\n"
