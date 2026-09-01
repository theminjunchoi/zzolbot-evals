"""torch 어댑터가 mlx와 **같은 판정**을 내리는지 고정한다.

여기서 갈리면 재현 대조가 무의미해진다. 두 백엔드의 차이가 나왔을 때 모델 차이인지
제약 구현 차이인지 못 가르기 때문이다.

가장 중요한 검사는 **프롬프트 길이를 빼는가**다. mlx는 생성 토큰만 넘기고 HF는 프롬프트를
포함한 전체를 넘긴다. 이걸 안 빼면 마커를 프롬프트 안에서 찾아 제약이 엉뚱하게 걸린다.
"""

from __future__ import annotations

import pytest

from harness.constrained import CitationConstraint, TorchCitationProcessor

torch = pytest.importorskip("torch")

LINE_A = "[14:10] ERROR alpha"
LINE_B = "[14:25] ERROR beta"


class CharTokenizer:
    """문자 하나 = 토큰 하나. tests/test_constrained.py와 같은 것을 쓴다."""

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        return [ord(c) for c in text]

    def decode(self, ids) -> str:
        return "".join(chr(i) for i in ids)


VOCAB = 0x3000


def make(prompt: str = ""):
    c = CitationConstraint(CharTokenizer(), [LINE_A, LINE_B])
    return TorchCitationProcessor(c, len(prompt)), c


def ids(*texts: str):
    return torch.tensor([[ord(ch) for ch in t] for t in texts], dtype=torch.long)


def flat_scores(rows: int = 1):
    return torch.zeros(rows, VOCAB)


def allowed_of(scores_row):
    return sorted(int(i) for i in (scores_row > float("-inf")).nonzero().flatten())


def test_프롬프트를_빼지_않으면_생기는_오독을_막는다():
    """프롬프트 안에 마커가 있어도 생성 쪽이 비어 있으면 제약이 걸리면 안 된다."""
    prompt = '기존 답변 예시: {"evidenceLine": "[14:'
    proc, _ = make(prompt)
    out = proc(ids(prompt), flat_scores())
    assert torch.isfinite(out[0]).all(), "프롬프트를 생성분으로 오독해 제약이 걸렸다"


def test_필드가_열리면_로그_첫_글자나_닫는_따옴표만_남는다():
    prompt = "P" * 7
    proc, _ = make(prompt)
    out = proc(ids(prompt + '{"evidenceLine": "'), flat_scores())
    assert allowed_of(out[0]) == sorted([ord("["), ord('"')])


def test_트라이를_따라가면_다음_글자만_남는다():
    prompt = "P" * 3
    proc, _ = make(prompt)
    out = proc(ids(prompt + '{"evidenceLine": "[14:'), flat_scores())
    assert allowed_of(out[0]) == sorted({ord("1"), ord("2")})   # [14:10 과 [14:25


def test_인용_필드_밖에서는_로짓을_건드리지_않는다():
    prompt = "P" * 5
    proc, _ = make(prompt)
    before = flat_scores()
    before[0, 42] = 1.5
    out = proc(ids(prompt + '{"summary": "무언가'), before.clone())
    assert torch.isfinite(out[0]).all()
    assert out[0, 42].item() == pytest.approx(1.5)


def test_mlx와_같은_판정을_쓴다():
    """torch 경로가 CitationConstraint.allowed_tokens를 그대로 쓰는지 확인한다.

    제약 로직이 두 벌이 되면 그 자체가 백엔드 불일치의 후보가 된다.
    """
    prompt = "P" * 4
    proc, c = make(prompt)
    body = '{"evidenceLine": "[14:10] ERROR al'
    expected = c.allowed_tokens([ord(ch) for ch in body])
    out = proc(ids(prompt + body), flat_scores())
    assert allowed_of(out[0]) == sorted(expected)


def test_배치_각_행을_독립으로_제약한다():
    """best-of-n은 여러 행을 한 번에 넘긴다. 행마다 진행 상태가 다르다."""
    prompt = "PP"
    proc, _ = make(prompt)
    a = prompt + '{"evidenceLine": "[14:'      # 제약 구간
    b = prompt + '{"summary": "abcdefg'         # 제약 밖
    b += "x" * (len(a) - len(b))                # 배치는 길이가 같아야 한다
    assert len(a) == len(b)
    out = proc(ids(a, b), flat_scores(2))
    assert allowed_of(out[0]) == sorted({ord("1"), ord("2")})
    assert torch.isfinite(out[1]).all()
