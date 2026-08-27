"""인용 필드를 실제 로그 줄로만 생성하도록 강제하는 제약 디코더.

배경. 소형 모델의 인용 실패 대부분이 판단이 아니라 **전사 오류**다. 옳은 줄을 고르고
밀리초 두 자리를 틀린다(유사도 99%인 실측 사례가 있다). 이건 학습으로 고칠 수도 있지만
디코딩 단계에서 **구조적으로 불가능하게** 만들 수도 있다.

방법. `"evidenceLine": "` 이 나온 뒤부터는 다음 토큰을 **허용된 로그 줄들의 토큰 트라이**로
제한한다. 줄 하나를 끝까지 쓰면 닫는 따옴표만 허용한다. 트라이는 각 로그 줄을 한 번 토큰화해
만들므로 어휘 전체를 훑지 않는다.

한계. 이 제약은 "원문 그대로"만 보장하고 **어느 줄을 고르는지는 보장하지 않는다.**
잘못된 줄을 고르는 실패는 그대로 남는다. 그게 학습이 담당할 몫이고, 두 팔을 비교하는
이유이기도 하다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class _Node:
    children: dict[int, "_Node"] = field(default_factory=dict)
    terminal: bool = False


def build_trie(sequences: list[list[int]]) -> _Node:
    root = _Node()
    for seq in sequences:
        node = root
        for token in seq:
            node = node.children.setdefault(token, _Node())
        node.terminal = True
    return root


class CitationConstraint:
    """생성 토큰을 보고 인용 필드 안에서만 트라이 제약을 건다.

    상태를 따로 들고 있지 않고 **매 호출마다 지금까지 생성된 토큰을 디코드해 판정**한다.
    호출 순서가 흐트러져도 상태가 어긋나지 않는다.
    """

    MARKER = '"evidenceLine":'

    def __init__(self, tokenizer, log_samples: list[str]):
        self._tok = tokenizer
        # JSON 문자열 안에 들어갈 형태로 만든다. json.dumps가 붙이는 바깥 따옴표는 뗀다.
        self._bodies = [json.dumps(line, ensure_ascii=False)[1:-1] for line in log_samples]
        self._trie = build_trie([tokenizer.encode(b, add_special_tokens=False)
                                 for b in self._bodies])
        quote = tokenizer.encode('"', add_special_tokens=False)
        self._quote_tokens = [t for t in quote if t is not None]

    def _generated_text(self, tokens) -> str:
        """mlx는 프롬프트를 뺀 **생성 토큰만** 프로세서에 넘긴다. 프롬프트 길이를 빼면
        항상 빈 문자열이 되어 제약이 한 번도 걸리지 않는다(실제로 겪었다)."""
        if len(tokens) == 0:
            return ""
        return self._tok.decode(tokens.tolist() if hasattr(tokens, "tolist") else list(tokens))

    def _field_token_ids(self, tokens) -> list[int] | None:
        """인용 필드 값이 시작됐다면 그 안에서 생성된 토큰 id들을 돌려준다.

        문자열 위치가 아니라 토큰 단위가 필요하므로, 필드 시작 이후 텍스트를 다시 토큰화한다.
        토큰 경계가 어긋날 수 있으나 트라이가 이미 강제한 경로라 실제로는 일치한다.
        """
        text = self._generated_text(tokens)
        at = text.rfind(self.MARKER)
        if at == -1:
            return None
        rest = text[at + len(self.MARKER):]
        open_quote = rest.find('"')
        if open_quote == -1:
            return None
        body = rest[open_quote + 1:]
        if '"' in body:  # 값이 이미 닫혔다
            return None
        return self._tok.encode(body, add_special_tokens=False) if body else []

    def allowed_tokens(self, tokens) -> list[int] | None:
        """다음에 올 수 있는 토큰 id들. 제약이 필요 없는 구간이면 None."""
        ids = self._field_token_ids(tokens)
        if ids is None:
            return None
        node = self._trie
        for token in ids:
            node = node.children.get(token)
            if node is None:
                return None  # 트라이를 벗어났다. 제약을 풀어 무한 루프를 막는다
        allowed = list(node.children)
        if node.terminal:
            allowed.extend(self._quote_tokens)
        return allowed or None

    def __call__(self, tokens, logits):
        import mlx.core as mx

        allowed = self.allowed_tokens(tokens)
        if allowed is None:
            return logits
        mask = mx.full(logits.shape, -mx.inf)
        idx = mx.array(allowed)
        mask[..., idx] = logits[..., idx]
        return mask
