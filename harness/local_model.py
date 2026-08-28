"""로컬 MLX 모델을 LLM 포트로 붙인다.

분석기를 로컬로 돌리면 평가에서 API 호출이 judge 하나로 줄고, 학습한 어댑터를 끼워
같은 하네스로 학습 전후를 비교할 수 있다. adapter_path가 그 교체 지점이다.

소형 모델은 JSON을 코드 펜스로 감싸거나 앞뒤에 설명을 붙이는 일이 잦다. 그건 태스크 실패가
아니라 출력 형식 문제이므로 여기서 흡수하고, 정말 JSON이 없을 때만 실패로 넘긴다.
"""

from __future__ import annotations

import re

from harness.llm import LlmJsonClient

DEFAULT_MODEL = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> str:
    """모델 출력에서 JSON 객체 하나를 꺼낸다. 없으면 원문을 그대로 돌려준다."""
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    if start == -1:
        return text.strip()
    depth, in_string, escaped = 0, False, False
    for i in range(start, len(text)):
        char = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text[start:].strip()


class MlxJsonClient(LlmJsonClient):

    def __init__(self, model_path: str = DEFAULT_MODEL, adapter_path: str | None = None,
                 max_tokens: int = 700, temperature: float = 0.0,
                 constrained: bool = False):
        """constrained면 인용 필드를 프롬프트에 실린 로그 줄로만 생성하도록 제약한다.

        로그 줄은 프롬프트에서 뽑는다. 시나리오를 따로 넘기지 않아도 되므로 LlmJsonClient
        인터페이스가 그대로 유지된다.
        """
        from mlx_lm import load

        self._model, self._tokenizer = load(model_path, adapter_path=adapter_path)
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._constrained = constrained

    def generate_json(self, system_instruction: str, prompt: str) -> str:
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ]
        text = self._tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        processors = None
        if self._constrained:
            from harness.constrained import CitationConstraint

            lines = [l[2:] for l in prompt.splitlines() if l.startswith("- [")]
            if lines:
                processors = [CitationConstraint(self._tokenizer, lines)]
        out = generate(self._model, self._tokenizer, prompt=text,
                       max_tokens=self._max_tokens, verbose=False,
                       logits_processors=processors,
                       sampler=make_sampler(temp=self._temperature))
        return extract_json(out)
