"""도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Alert:
    alertname: str
    severity: str
    fingerprint: str
    summary: str
    description: str
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Scenario:
    """골든 시나리오. 자바 하네스의 SeedFile 스키마와 1:1 대응한다."""

    name: str
    question: str
    rubric: str
    source: str
    alert: Alert
    log_samples: tuple[str, ...]
    log_environment: str


@dataclass(frozen=True)
class Analysis:
    """분석기 출력. grounded는 접지 검증(GroundingPipeline)을 통과했는지다."""

    summary: str
    root_cause_hypothesis: str
    suggested_actions: tuple[str, ...]
    evidence_found: bool
    evidence_line: str
    grounded: bool = False


@dataclass(frozen=True)
class JudgeScore:
    accuracy: int
    groundedness: int
    hallucination_detected: bool
    verdict: str  # "PASS" | "FAIL"
    rationale: str

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"


@dataclass(frozen=True)
class TrialResult:
    """시나리오 1회 시행의 결과. 시행은 서로 독립이다 (통계 목적, 조기 중단 없음)."""

    scenario_name: str
    trial: int
    answer: str
    score: JudgeScore
    analyzer_latency_ms: int
    error: str | None = None
