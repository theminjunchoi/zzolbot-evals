"""GBNF 인용 문법 테스트.

두 겹 이스케이프가 겹치는 자리라 눈으로 보고 넘기면 안 된다. 실제 llama.cpp에 먹이는
것은 별도 스모크로 확인하고, 여기서는 문자열 생성 규약만 못박는다.
"""

from harness.gbnf import citation_grammar


def test_로그_줄이_리터럴로_들어간다():
    grammar = citation_grammar(["[ERROR] 방 참가 실패"])
    assert 'line0 ::= "[ERROR] 방 참가 실패"' in grammar


def test_빈_인용을_허용한다():
    # 근거 없음이 정답인 시나리오에서 빈 문자열을 막으면 JSON을 못 닫는다(리포트 14번)
    assert 'cite ::= "\\"\\"" |' in citation_grammar(["a"])


def test_따옴표가_두_겹으로_이스케이프된다():
    # JSON 본문에서 `"`는 `\"` 두 글자이고, GBNF 리터럴 안에서 그 역슬래시를 또 escape 한다
    grammar = citation_grammar(['msg="down"'])
    assert 'line0 ::= "msg=\\\\\\"down\\\\\\""' in grammar


def test_역슬래시가_이스케이프된다():
    grammar = citation_grammar([r"C:\path"])
    assert r'line0 ::= "C:\\\\path"' in grammar


def test_중복_줄은_한_번만_들어간다():
    grammar = citation_grammar(["같은 줄", "같은 줄", "다른 줄"])
    assert "line2 ::=" not in grammar
    assert "anyline ::= line0 | line1" in grammar


def test_인용이_닫히면_객체를_닫는_것만_남는다():
    # 반복 생성 방지. cite 뒤에 ws와 닫는 중괄호만 온다
    assert '"\\"evidenceLine\\":" ws cite ws "}"' in citation_grammar(["a"])
