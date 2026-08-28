"""제약 디코더가 언제 제약을 걸고 언제 풀어주는지 고정한다.

토크나이저 없이도 논리를 확인할 수 있게 가짜 토크나이저를 쓴다. 문자 하나가 토큰 하나다.
"""

from __future__ import annotations

from harness.constrained import CitationConstraint, build_trie


class CharTokenizer:
    """문자 하나 = 토큰 하나. 코드 포인트를 그대로 id로 쓴다."""

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        return [ord(c) for c in text]

    def decode(self, ids) -> str:
        return "".join(chr(i) for i in ids)


LINE_A = "[14:10] ERROR alpha"
LINE_B = "[14:25] ERROR beta"


def make() -> CitationConstraint:
    return CitationConstraint(CharTokenizer(), [LINE_A, LINE_B])


def tokens(text: str) -> list[int]:
    return [ord(c) for c in text]


def test_트라이는_공통_접두를_공유한다():
    trie = build_trie([[1, 2, 3], [1, 2, 4]])
    assert set(trie.children) == {1}
    assert set(trie.children[1].children[2].children) == {3, 4}
    assert trie.children[1].children[2].children[3].terminal


def test_인용_필드_밖에서는_제약하지_않는다():
    c = make()
    assert c.allowed_tokens(tokens('{"summary": "무언가')) is None


def test_필드가_열리면_로그_첫_글자나_닫는_따옴표만_허용한다():
    c = make()
    allowed = c.allowed_tokens(tokens('{"evidenceLine": "'))
    assert sorted(allowed) == sorted([ord("["), ord('"')])


def test_공통_접두_이후에는_갈래가_둘이다():
    c = make()
    allowed = c.allowed_tokens(tokens('{"evidenceLine": "[14:'))
    assert sorted(allowed) == sorted([ord("1"), ord("2")])


def test_한_줄을_끝까지_쓰면_닫는_따옴표를_허용한다():
    c = make()
    allowed = c.allowed_tokens(tokens(f'{{"evidenceLine": "{LINE_A}'))
    assert ord('"') in allowed


def test_값이_닫힌_뒤에는_객체를_닫는_토큰만_허용한다():
    c = make()
    allowed = c.allowed_tokens(tokens(f'{{"evidenceLine": "{LINE_A}"'))
    assert allowed is not None and ord("}") in allowed


def test_트라이를_벗어나면_제약을_푼다():
    """강제하고 있으므로 실제로는 일어나지 않지만, 일어나면 무한 루프를 막아야 한다."""
    c = make()
    assert c.allowed_tokens(tokens('{"evidenceLine": "ZZZ')) is None


def test_생성이_비었으면_제약하지_않는다():
    """mlx는 프롬프트를 뺀 생성 토큰만 넘긴다."""
    c = make()
    assert c.allowed_tokens([]) is None


def test_따옴표가_들어간_로그도_이스케이프해_다룬다():
    tok = CharTokenizer()
    c = CitationConstraint(tok, ['ERROR msg="boom"'])
    # JSON 이스케이프 후에는 \" 로 시작하는 경로가 있어야 한다
    allowed = c.allowed_tokens(tokens('{"evidenceLine": "ERROR msg='))
    assert allowed == [ord("\\")]


def test_빈_인용을_허용한다():
    """evidenceFound=false이면 evidenceLine은 빈 문자열이어야 한다.
    막으면 모델이 긴 로그 줄을 억지로 쓰다 토큰 상한에서 JSON을 못 닫는다."""
    c = make()
    allowed = c.allowed_tokens(tokens('{"evidenceLine": "'))
    assert ord('"') in allowed          # 즉시 닫을 수 있어야 한다
    assert ord("[") in allowed          # 인용을 시작할 수도 있어야 한다


def test_값이_닫히면_중괄호로만_이어진다():
    """evidenceLine은 스키마의 마지막 필드다. 값이 닫히면 객체를 닫는 것 외에 올 것이 없다.
    강제하지 않으면 긴 줄을 통과한 뒤 모델이 필드를 다시 쓰는 반복 생성에 빠진다."""
    c = make()
    allowed = c.allowed_tokens(tokens(f'{{"evidenceLine": "{LINE_A}"'))
    assert ord("}") in allowed
    assert ord("[") not in allowed


def test_객체가_닫히면_제약을_푼다():
    c = make()
    assert c.allowed_tokens(tokens(f'{{"evidenceLine": "{LINE_A}"}}')) is None
