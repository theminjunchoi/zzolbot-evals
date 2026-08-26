"""후보의 내부 정합성 검사. rule 필터가 잡지 못하는 의미 수준 결함을 거른다.

**정답이 무엇인지 판정하게 하면 안 된다.** 스크리너에게 "이 로그가 알림을 뒷받침하는가"를 물으면
피평가 모델과 같은 오판을 하는 순간 그 시나리오가 걸러진다. 즉 모델이 틀리는 어려운 시나리오만
골라서 제거하는 필터가 되어, 벤치마크를 다시 쉽게 만든다(outbox-33 같은 사례가 사라진다).

그래서 묻는 것은 하나뿐이다: **rubric이 로그에 대해 서술한 사실이 실제 로그와 모순되는가.**
판정이 아니라 모순 검출이므로 난이도와 무관하게 동작한다.

실제 사례: "무관 함정" 축인데 생성기가 QR 실패 로그의 error 슬롯에 'No space left on device'를
넣어 로그가 디스크 부족의 직접 증거가 된 후보가 있었다(2026-08-26 disk-08). rule 필터는 형식만
보므로 통과했고 사람 검토도 놓쳤다. 이 검사기가 겨냥하는 결함이 그것이다.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from harness.llm import LlmJsonClient

SYSTEM_INSTRUCTION = """\
너는 운영 모니터링 평가 시나리오의 내부 정합성을 검사한다.

**정답이 무엇인지 판정하지 마라.** 로그가 알림의 근거가 되는지 아닌지는 네 판단 대상이 아니다.
너는 오직 "채점 기준(rubric)이 로그에 대해 서술한 사실"과 "실제 로그 내용"이 서로 모순되는지만 본다.

모순으로 볼 것:
1. rubric이 "로그는 X와 무관하다" 또는 "X 관련 로그가 전혀 없다"고 서술했는데, 로그에 X를 직접
   가리키는 문자열이 있는 경우. (예: 디스크와 무관하다고 했는데 로그에 'No space left on device'가 있음)
2. rubric이 "로그가 Y를 보여준다"고 서술했는데, 로그에 Y에 해당하는 내용이 없는 경우.
3. rubric이 인용한 컴포넌트명, 수치, 스트림명이 로그나 알림 어디에도 없는 경우.

모순이 아닌 것:
- 로그가 알림과 관련이 있는지에 대한 네 의견과 rubric의 판정이 다른 것. 이건 모순이 아니다.
- rubric이 어렵거나 미묘한 판단을 요구하는 것.
- 표현이 다르지만 같은 대상을 가리키는 것.

아래 JSON으로만 응답하라.
{
  "contradiction": true 또는 false,
  "reason": "모순이면 어떤 서술과 어떤 로그가 어긋나는지 한국어 한두 문장. 아니면 빈 문자열"
}"""


@dataclass(frozen=True)
class ScreenResult:
    contradiction: bool
    reason: str


class CandidateScreener(ABC):
    @abstractmethod
    def screen(self, candidate: dict) -> ScreenResult: ...


class LlmScreener(CandidateScreener):
    def __init__(self, client: LlmJsonClient):
        self._client = client

    def screen(self, candidate: dict) -> ScreenResult:
        try:
            raw = self._client.generate_json(SYSTEM_INSTRUCTION, build_prompt(candidate))
            node = json.loads(raw)
        except Exception as e:  # noqa: BLE001 - 스크리닝 실패가 배치를 죽이지 않게
            return ScreenResult(False, f"스크리닝 실패(통과 처리): {e}")
        return ScreenResult(bool(node.get("contradiction", False)), str(node.get("reason") or ""))


def build_prompt(candidate: dict) -> str:
    alert = candidate.get("alert") or {}
    lines = [
        "[알림]",
        f"{alert.get('alertname')} ({alert.get('severity')})",
        f"요약: {alert.get('summary')}",
        f"설명: {alert.get('description')}",
        "",
        "[로그]",
        *(f"- {line}" for line in candidate.get("logSamples") or []),
        "",
        "[채점 기준]",
        candidate.get("rubric") or "",
    ]
    return "\n".join(lines) + "\n"
