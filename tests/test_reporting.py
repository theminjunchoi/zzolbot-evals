import json

from harness.domain import JudgeScore, TrialResult
from harness.reporting import JsonlSink, ReportBuilder


def result(name: str, trial: int, verdict: str, acc: int = 5) -> TrialResult:
    return TrialResult(name, trial, "답변", JudgeScore(acc, 5, False, verdict, "이유"), 100)


def test_시나리오별로_집계한다():
    results = [
        result("a", 1, "PASS"), result("a", 2, "FAIL", acc=2),
        result("b", 1, "PASS"), result("b", 2, "PASS"),
    ]

    stats = ReportBuilder().aggregate(results)

    by_name = {s.name: s for s in stats}
    assert by_name["a"].passes == 1 and by_name["a"].trials == 2
    assert by_name["a"].pass_rate == 0.5
    assert by_name["a"].mean_accuracy == 3.5
    assert by_name["b"].pass_rate == 1.0


def test_마크다운_리포트에_요약과_행이_들어간다():
    builder = ReportBuilder()
    stats = builder.aggregate([result("a", 1, "PASS"), result("b", 1, "FAIL")])

    md = builder.to_markdown("test-label", "gemini-2.5-flash", stats)

    assert "시행 PASS율: 1/2" in md
    assert "| a | 1/1 |" in md
    assert "| b | 0/1 |" in md


def test_jsonl_sink는_시행마다_한_줄을_남긴다(tmp_path):
    path = tmp_path / "out.jsonl"
    sink = JsonlSink(path)

    sink.write(result("a", 1, "PASS"))
    sink.write(result("a", 2, "FAIL"))

    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 2
    assert rows[0]["scenario_name"] == "a"
    assert rows[1]["score"]["verdict"] == "FAIL"
