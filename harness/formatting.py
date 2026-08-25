"""분석 결과를 judge가 채점할 텍스트로 평탄화한다.

자바 MonitorScenarioEvaluator.flatten과 동일한 계약이다. rubric이 '근거 발견: 아니오' 같은
라벨 문자열을 직접 참조하므로, 이 형식이 달라지면 채점이 무너진다.
"""

from __future__ import annotations

from harness.domain import Analysis


class AnswerFormatter:

    def flatten(self, analysis: Analysis) -> str:
        lines = [
            f"요약: {analysis.summary}",
            f"근거 발견: {'예' if analysis.grounded else '아니오'}",
            f"원인 가설: {analysis.root_cause_hypothesis or '(없음)'}",
        ]
        if not analysis.suggested_actions:
            lines.append("제안 조치: (없음)")
        else:
            lines.append("제안 조치:")
            lines.extend(f"- {action}" for action in analysis.suggested_actions)
        return "\n".join(lines)
