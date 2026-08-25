from harness.analyzer import Analyzer
from harness.domain import Alert, Analysis, JudgeScore, Scenario
from harness.judge import Judge
from harness.runner import EvalRunner


def make_scenario(name: str, log: str) -> Scenario:
    return Scenario(
        name=name, question="q", rubric="r", source="MANUAL",
        alert=Alert("A", "warning", "fp", "sum", "desc", {}),
        log_samples=(log,), log_environment="prod")


class StubAnalyzer(Analyzer):
    """호출 순서대로 미리 정한 Analysis를 돌려준다."""

    def __init__(self, analyses):
        self._analyses = list(analyses)
        self.calls = 0

    def analyze(self, scenario):
        analysis = self._analyses[self.calls % len(self._analyses)]
        self.calls += 1
        if isinstance(analysis, Exception):
            raise analysis
        return analysis


class StubJudge(Judge):
    def __init__(self, verdict="PASS"):
        self.answers = []
        self._verdict = verdict

    def evaluate(self, question, rubric, answer):
        self.answers.append(answer)
        return JudgeScore(5, 5, False, self._verdict, "stub")


LOG = "[2026-08-25 10:00:00.000] [ERROR] [,] --- [t] c.g.Foo : 문제: id=1"


def grounded_analysis() -> Analysis:
    return Analysis("요약", "가설", ("조치",), True, LOG)


def test_시행은_독립이며_PASS가_나와도_반복을_계속한다():
    analyzer = StubAnalyzer([grounded_analysis()])
    judge = StubJudge("PASS")
    runner = EvalRunner(analyzer, judge)

    results = runner.run([make_scenario("s1", LOG)], repeats=3)

    assert len(results) == 3
    assert analyzer.calls == 3
    assert [r.trial for r in results] == [1, 2, 3]


def test_접지_강등이_judge에_전달되는_답변에_반영된다():
    fabricated = Analysis("요약", "가설", (), True, "지어낸 인용")
    judge = StubJudge()
    runner = EvalRunner(StubAnalyzer([fabricated]), judge)

    runner.run([make_scenario("s1", LOG)], repeats=1)

    assert "근거 발견: 아니오" in judge.answers[0]
    assert "원인 가설: (없음)" in judge.answers[0]


def test_분석기_예외는_해당_시행만_FAIL로_기록한다():
    analyzer = StubAnalyzer([RuntimeError("boom"), grounded_analysis()])
    runner = EvalRunner(analyzer, StubJudge())

    results = runner.run([make_scenario("s1", LOG)], repeats=2)

    assert not results[0].score.passed
    assert results[0].error is not None
    assert results[1].score.passed


def test_결과_콜백이_시행마다_호출된다():
    seen = []
    runner = EvalRunner(StubAnalyzer([grounded_analysis()]), StubJudge(),
                        on_result=seen.append)

    runner.run([make_scenario("s1", LOG), make_scenario("s2", LOG)], repeats=2)

    assert len(seen) == 4
