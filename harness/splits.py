"""dev/test 분할 관리.

개선 실험은 dev만 보고, 최종 보고 숫자는 한 번도 보지 않은 test에서 낸다.
같은 셋을 보며 프롬프트를 고치는 것을 반복하면 개선인지 평가셋 암기인지 구별할 수 없어진다.

현재 dev에는 프롬프트 튜닝에 이미 사용된 시나리오(오염)와 다음 실험의 표적이 들어 있다.
새로 합성한 시나리오는 튜닝 표적으로 쓰지 않는 한 test로 보내 test를 키운다.
"""

from __future__ import annotations

import json
from pathlib import Path

from harness.domain import Scenario

ALL = "all"


class SplitManifest:

    def __init__(self, assignments: dict[str, list[str]]):
        self._assignments = {name: list(members) for name, members in assignments.items()}

    @classmethod
    def load(cls, path: Path) -> SplitManifest:
        return cls(json.loads(path.read_text(encoding="utf-8")))

    @property
    def names(self) -> list[str]:
        return sorted(self._assignments)

    def members(self, split: str) -> set[str]:
        if split == ALL:
            return {name for members in self._assignments.values() for name in members}
        if split not in self._assignments:
            raise KeyError(f"알 수 없는 분할: {split} (가능: {', '.join(self.names)}, {ALL})")
        return set(self._assignments[split])

    def filter(self, scenarios: list[Scenario], split: str) -> list[Scenario]:
        if split == ALL:
            return scenarios
        allowed = self.members(split)
        return [s for s in scenarios if s.name in allowed]
