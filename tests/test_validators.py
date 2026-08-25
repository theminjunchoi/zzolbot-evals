"""검증기 자가 검증: 손으로 검증한 기존 골든셋 20종이 전부 통과해야 필터가 올바르다."""

import json
from pathlib import Path

from synthesis.validators import FilterStats, default_validators, validate

GOLDEN_DIR = Path(__file__).parent.parent / "golden-set" / "monitor"


def load_golden():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(GOLDEN_DIR.glob("*.json"))]


def test_기존_골든셋_20종은_전부_필터를_통과한다():
    validators = default_validators(existing_names=set())
    failures_found = {}
    for candidate in load_golden():
        failures = validate(candidate, validators)
        flat = [r for reasons in failures.values() for r in reasons]
        if flat:
            failures_found[candidate["name"]] = flat

    assert failures_found == {}, failures_found


def test_존재하지_않는_알림은_탈락한다():
    candidate = load_golden()[0]
    candidate["alert"]["alertname"] = "MadeUpAlert"

    failures = validate(candidate, default_validators())

    assert any("존재하지 않는 알림" in r for r in failures["alert"])


def test_지어낸_로그_메시지는_탈락한다():
    candidate = load_golden()[0]
    candidate["logSamples"] = [
        "[2026-08-25 10:00:00.000] [ERROR] [,] --- [http-nio-8080-exec-1] c.fake.Logger : 이런 메시지는 코드에 없다"
    ]

    failures = validate(candidate, default_validators())

    assert any("카탈로그에 없는" in r for r in failures["log-line"])


def test_로그_패턴이_깨지면_탈락한다():
    candidate = load_golden()[0]
    candidate["logSamples"] = ["2026-08-25 10:00 ERROR something broke"]

    failures = validate(candidate, default_validators())

    assert any("패턴 불일치" in r for r in failures["log-line"])


def test_expected와_rubric의_방향이_어긋나면_탈락한다():
    candidate = load_golden()[0]
    candidate["expected"] = "예"
    candidate["rubric"] = "'근거 발견: 아니오'로 판정하면 정답. 아니면 오답."

    failures = validate(candidate, default_validators())

    assert any("expected=예" in r for r in failures["rubric"])


def test_이름이_기존과_겹치면_탈락한다():
    candidate = load_golden()[0]

    failures = validate(candidate, default_validators(existing_names={candidate["name"]}))

    assert failures["duplicate"]


def test_통계는_검증기별_탈락을_집계한다():
    stats = FilterStats()
    stats.record("a", {"schema": [], "alert": ["문제"]})
    stats.record("b", {"schema": [], "alert": []})

    assert stats.total == 2
    assert stats.passed == 1
    assert stats.dropped_by["alert"] == 1
