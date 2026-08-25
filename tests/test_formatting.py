from harness.domain import Analysis
from harness.formatting import AnswerFormatter


def test_접지된_분석의_평탄화_형식():
    analysis = Analysis(
        summary="요약문", root_cause_hypothesis="가설문",
        suggested_actions=("조치1", "조치2"), evidence_found=True,
        evidence_line="line", grounded=True)

    text = AnswerFormatter().flatten(analysis)

    assert text == "요약: 요약문\n근거 발견: 예\n원인 가설: 가설문\n제안 조치:\n- 조치1\n- 조치2"


def test_근거_없음의_평탄화_형식():
    analysis = Analysis(
        summary="근거를 찾지 못했습니다.", root_cause_hypothesis="",
        suggested_actions=(), evidence_found=False, evidence_line="", grounded=False)

    text = AnswerFormatter().flatten(analysis)

    assert text == "요약: 근거를 찾지 못했습니다.\n근거 발견: 아니오\n원인 가설: (없음)\n제안 조치: (없음)"
