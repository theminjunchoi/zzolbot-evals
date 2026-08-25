"""LLM judge 채점. 자바 GeminiJudgeClient와 동일한 계약이다."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from harness.domain import JudgeScore
from harness.llm import LlmJsonClient

# 자바 GeminiJudgeClient.SYSTEM_INSTRUCTION과 동일해야 한다.
SYSTEM_INSTRUCTION = """\
너는 운영 진단 봇의 답변을 채점하는 엄격한 평가자다.
주어진 질문, 채점 기준(rubric), 봇의 답변을 보고 아래 JSON 스키마로만 응답하라.
{
  "accuracy": 0~5 정수 (rubric의 핵심을 맞혔는가),
  "groundedness": 0~5 정수 (도구 결과/근거에 기반했는가),
  "hallucinationDetected": true/false (없는 사실·수치를 지어냈는가),
  "verdict": "PASS" 또는 "FAIL",
  "rationale": "판정 근거 한국어 한두 문장"
}
설명 텍스트 없이 JSON 객체 하나만 출력하라."""


class Judge(ABC):
    @abstractmethod
    def evaluate(self, question: str, rubric: str, answer: str) -> JudgeScore: ...


class GeminiJudge(Judge):
    def __init__(self, client: LlmJsonClient):
        self._client = client

    def evaluate(self, question: str, rubric: str, answer: str) -> JudgeScore:
        prompt = build_prompt(question, rubric, answer)
        try:
            return parse_score(self._client.generate_json(SYSTEM_INSTRUCTION, prompt))
        except json.JSONDecodeError as e:
            return JudgeScore(0, 0, False, "FAIL", f"judge 응답 파싱 실패: {e}")


def build_prompt(question: str, rubric: str, answer: str) -> str:
    return f"[질문]\n{question}\n\n[채점 기준]\n{rubric}\n\n[봇의 답변]\n{answer}\n"


def parse_score(raw_json: str) -> JudgeScore:
    node = json.loads(raw_json)
    verdict = "PASS" if node.get("verdict") == "PASS" else "FAIL"
    return JudgeScore(
        accuracy=_clamp(node.get("accuracy", 0)),
        groundedness=_clamp(node.get("groundedness", 0)),
        hallucination_detected=bool(node.get("hallucinationDetected", False)),
        verdict=verdict,
        rationale=str(node.get("rationale") or ""),
    )


def _clamp(value) -> int:
    try:
        return max(0, min(5, int(value)))
    except (TypeError, ValueError):
        return 0
