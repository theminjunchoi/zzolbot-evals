from harness.judge import build_prompt, parse_score


def test_정상_응답을_파싱한다():
    raw = '{"accuracy": 5, "groundedness": 4, "hallucinationDetected": false, "verdict": "PASS", "rationale": "좋음"}'

    score = parse_score(raw)

    assert score.passed
    assert score.accuracy == 5
    assert score.groundedness == 4


def test_범위를_벗어난_점수는_0에서_5로_클램프한다():
    score = parse_score('{"accuracy": 9, "groundedness": -3, "verdict": "PASS"}')

    assert score.accuracy == 5
    assert score.groundedness == 0


def test_verdict가_PASS가_아니면_전부_FAIL이다():
    assert not parse_score('{"verdict": "pass"}').passed
    assert not parse_score('{"verdict": "OK"}').passed
    assert not parse_score('{}').passed


def test_judge_프롬프트는_자바와_같은_섹션_라벨을_쓴다():
    prompt = build_prompt("질문내용", "기준내용", "답변내용")

    assert prompt == "[질문]\n질문내용\n\n[채점 기준]\n기준내용\n\n[봇의 답변]\n답변내용\n"
