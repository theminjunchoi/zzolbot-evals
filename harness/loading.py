"""시나리오 로딩."""

from __future__ import annotations

import json
from pathlib import Path

from harness.domain import Alert, Scenario


class ScenarioLoader:
    """디렉터리의 *.json을 Scenario로 읽는다. 스키마가 깨진 파일은 조용히 넘기지 않고 즉시 실패한다.

    자바 로더는 파싱 실패를 warn으로 삼켜 테스트가 게이트였지만, 여기서는 fail-fast가 게이트다.
    """

    REQUIRED_FIELDS = ("name", "question", "rubric", "source", "alert", "logSamples", "logEnvironment")

    def load_dir(self, directory: Path) -> list[Scenario]:
        scenarios = [self.load_file(path) for path in sorted(directory.glob("*.json"))]
        if not scenarios:
            raise FileNotFoundError(f"시나리오 JSON이 없습니다: {directory}")
        return scenarios

    def load_file(self, path: Path) -> Scenario:
        return self.from_dict(json.loads(path.read_text(encoding="utf-8")), source=path.name)

    def from_dict(self, raw: dict, source: str = "<dict>") -> Scenario:
        path = source
        missing = [key for key in self.REQUIRED_FIELDS if key not in raw]
        if missing:
            raise ValueError(f"{path}: 필수 필드 누락 {missing}")
        alert_raw = raw["alert"]
        alert = Alert(
            alertname=alert_raw["alertname"],
            severity=alert_raw["severity"],
            fingerprint=alert_raw["fingerprint"],
            summary=alert_raw["summary"],
            description=alert_raw["description"],
            labels=dict(alert_raw.get("labels") or {}),
        )
        return Scenario(
            name=raw["name"],
            question=raw["question"],
            rubric=raw["rubric"],
            source=raw["source"],
            alert=alert,
            log_samples=tuple(raw["logSamples"]),
            log_environment=raw["logEnvironment"],
            expected=str(raw.get("expected") or ""),
        )
