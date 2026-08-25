"""평가 실행기. 시나리오와 시행 반복을 순회하며 분석, 접지, 평탄화, 채점을 조율한다.

자바 EvalRunner와 달리 시행은 서로 독립이고 PASS가 나와도 멈추지 않는다.
목적이 회귀 게이트가 아니라 통계(시나리오별 PASS율과 분산)이기 때문이다.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from harness.analyzer import Analyzer
from harness.domain import JudgeScore, Scenario, TrialResult
from harness.formatting import AnswerFormatter
from harness.grounding import GroundingPipeline
from harness.judge import Judge


class EvalRunner:

    def __init__(self, analyzer: Analyzer, judge: Judge,
                 grounding: GroundingPipeline | None = None,
                 formatter: AnswerFormatter | None = None,
                 on_result: Callable[[TrialResult], None] | None = None):
        self._analyzer = analyzer
        self._judge = judge
        self._grounding = grounding or GroundingPipeline()
        self._formatter = formatter or AnswerFormatter()
        self._on_result = on_result or (lambda result: None)

    def run(self, scenarios: list[Scenario], repeats: int = 1) -> list[TrialResult]:
        results = []
        for scenario in scenarios:
            for trial in range(1, repeats + 1):
                result = self._run_one(scenario, trial)
                results.append(result)
                self._on_result(result)
        return results

    def _run_one(self, scenario: Scenario, trial: int) -> TrialResult:
        try:
            start = time.monotonic()
            analysis = self._analyzer.analyze(scenario)
            latency_ms = int((time.monotonic() - start) * 1000)
            analysis = self._grounding.apply(analysis, scenario)
            answer = self._formatter.flatten(analysis)
            score = self._judge.evaluate(scenario.question, scenario.rubric, answer)
            return TrialResult(scenario.name, trial, answer, score, latency_ms)
        except Exception as e:  # noqa: BLE001 - 시행 하나의 실패가 전체 실행을 죽이지 않게
            failed = JudgeScore(0, 0, False, "FAIL", f"평가 중 예외: {e}")
            return TrialResult(scenario.name, trial, "평가 실패", failed, 0, error=str(e))
