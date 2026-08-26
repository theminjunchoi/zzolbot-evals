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


# 실험 변형. production은 팀 레포 GeminiJudgeClient와 문자열이 같아야 하며 수정하지 않는다.
# 캘리브레이션에서 원인 구체성 축의 일치율이 40%로 나왔다. judge가 "원인 가설이 다소
# 포괄적"이라고 인지하면서도 PASS를 주는 패턴이라, 인지한 것을 판정으로 연결하게 만든다.
# 마지막 항목은 반대 방향 가드다. 한쪽을 조이면 다른 쪽으로 넘어가기 쉽다.
SPECIFICITY_RULE = """

채점 시 반드시 지킬 것.
- 봇의 '근거 발견' 판정이 채점 기준이 요구하는 값과 다르면 accuracy는 1 이하이고 verdict는 FAIL이다.
- 판정이 맞아도, 원인 가설이 채점 기준이 지목하라고 한 대상(컴포넌트, 스트림, 실패 메커니즘)을
  구체적으로 짚지 못하고 "시스템 내부 문제", "일시적인 오류" 같은 일반적 표현에 머무르면
  accuracy는 3 이하이고 verdict는 FAIL이다. 방향만 맞은 것은 맞힌 것이 아니다.
- 반대로 판정과 원인이 채점 기준을 충족했다면, 표현이 조심스럽다거나 제안 조치가 비어 있다는
  이유로 감점하지 마라. 채점 기준이 요구하지 않은 요소는 채점 대상이 아니다."""


def _with_extra_rule(base: str, rule: str) -> str:
    marker = "\n설명 텍스트 없이"
    head, tail = base.split(marker, 1)
    return head + rule + marker + tail


JUDGE_VARIANTS: dict[str, str] = {
    "production": SYSTEM_INSTRUCTION,
    "specificity-aware": _with_extra_rule(SYSTEM_INSTRUCTION, SPECIFICITY_RULE),
}


class Judge(ABC):
    @abstractmethod
    def evaluate(self, question: str, rubric: str, answer: str) -> JudgeScore: ...


class GeminiJudge(Judge):
    def __init__(self, client: LlmJsonClient, system_instruction: str = SYSTEM_INSTRUCTION):
        self._client = client
        self._system_instruction = system_instruction

    def evaluate(self, question: str, rubric: str, answer: str) -> JudgeScore:
        prompt = build_prompt(question, rubric, answer)
        try:
            return parse_score(self._client.generate_json(self._system_instruction, prompt))
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
