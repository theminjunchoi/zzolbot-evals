"""스크리닝 단계 계약.

스크리너는 정답을 판정하지 않고 rubric과 로그의 모순만 본다. 판정을 시키면 피평가 모델이
틀리는 어려운 시나리오만 골라 제거하게 되어 벤치마크가 다시 쉬워진다.
"""

import json
from pathlib import Path

from harness.loading import ScenarioLoader
from synthesis.pipeline import BatchItem, SynthesisPipeline
from synthesis.screening import CandidateScreener, ScreenResult, build_prompt

GOLDEN_DIR = Path(__file__).parent.parent / "golden-set" / "monitor"


class StubGenerator:
    def __init__(self, candidate):
        self._candidate = candidate

    def generate(self, axis, alertname, exemplars, ordinal):
        return json.loads(json.dumps(self._candidate))


class StubScreener(CandidateScreener):
    def __init__(self, contradiction: bool):
        self._contradiction = contradiction
        self.calls = 0

    def screen(self, candidate):
        self.calls += 1
        return ScreenResult(self._contradiction, "모순" if self._contradiction else "")


def valid_candidate():
    raw = json.loads((GOLDEN_DIR / "monitor-db-pool-high-unrelated-game-errors.json").read_text(encoding="utf-8"))
    raw["name"] = "monitor-stub-candidate"
    return raw


def make_pipeline(tmp_path, screener, candidate=None):
    exemplars = ScenarioLoader().load_dir(GOLDEN_DIR)
    return SynthesisPipeline(
        StubGenerator(candidate or valid_candidate()), exemplars,
        {s.name for s in exemplars}, tmp_path, screener=screener)


AXIS_ITEM = None


def batch():
    from synthesis.axes import AXES
    return [BatchItem(AXES["unrelated-trap"], "DbConnectionPoolHigh", 1)]


def test_모순이_없으면_후보가_살아남는다(tmp_path):
    screener = StubScreener(contradiction=False)
    pipeline = make_pipeline(tmp_path, screener)

    saved = pipeline.run(batch(), on_progress=lambda _: None)

    assert len(saved) == 1
    assert screener.calls == 1


def test_모순이_있으면_탈락하고_사유가_통계에_남는다(tmp_path):
    pipeline = make_pipeline(tmp_path, StubScreener(contradiction=True))

    saved = pipeline.run(batch(), on_progress=lambda _: None)

    assert saved == []
    assert pipeline.stats.dropped_by["screen"] == 1


def test_rule_필터에서_이미_떨어지면_스크리닝을_부르지_않는다(tmp_path):
    broken = valid_candidate()
    broken["alert"]["alertname"] = "MadeUpAlert"
    screener = StubScreener(contradiction=False)
    pipeline = make_pipeline(tmp_path, screener, candidate=broken)

    pipeline.run(batch(), on_progress=lambda _: None)

    assert screener.calls == 0


def test_스크리닝_프롬프트는_알림과_로그와_기준을_담는다():
    prompt = build_prompt(valid_candidate())

    assert "[알림]" in prompt and "[로그]" in prompt and "[채점 기준]" in prompt
