from harness.domain import Alert, Analysis, Scenario
from harness.grounding import NO_EVIDENCE_SUMMARY, CitationExistsRule, GroundingPipeline


def scenario_with_logs(*logs: str) -> Scenario:
    return Scenario(
        name="s", question="q", rubric="r", source="MANUAL",
        alert=Alert("A", "warning", "fp", "sum", "desc", {}),
        log_samples=tuple(logs), log_environment="prod")


def analysis(evidence_found: bool, evidence_line: str) -> Analysis:
    return Analysis(
        summary="원래 요약", root_cause_hypothesis="원래 가설",
        suggested_actions=("조치",), evidence_found=evidence_found,
        evidence_line=evidence_line)


LOG = "[2026-08-25 10:00:00.000] [ERROR] [,] --- [t] c.g.Foo : 문제 발생: id=1"


def test_실재하는_인용은_접지를_통과한다():
    result = GroundingPipeline().apply(analysis(True, LOG), scenario_with_logs(LOG))

    assert result.grounded
    assert result.summary == "원래 요약"
    assert result.root_cause_hypothesis == "원래 가설"


def test_모델이_true라_해도_인용이_없으면_강등한다():
    result = GroundingPipeline().apply(
        analysis(True, "지어낸 로그 한 줄"), scenario_with_logs(LOG))

    assert not result.grounded
    assert result.summary == NO_EVIDENCE_SUMMARY
    assert result.root_cause_hypothesis == ""


def test_공백_차이는_무시하고_인용을_인정한다():
    cited = "[2026-08-25 10:00:00.000]  [ERROR]   [,] --- [t] c.g.Foo : 문제 발생: id=1"

    assert CitationExistsRule().holds(analysis(True, cited), scenario_with_logs(LOG))


def test_evidence_line이_비면_거짓이다():
    assert not CitationExistsRule().holds(analysis(True, "  "), scenario_with_logs(LOG))


def test_evidence_found가_false면_규칙과_무관하게_강등한다():
    result = GroundingPipeline().apply(analysis(False, LOG), scenario_with_logs(LOG))

    assert not result.grounded
    assert result.summary == NO_EVIDENCE_SUMMARY
