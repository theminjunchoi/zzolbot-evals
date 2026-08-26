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
    # 골든셋 원본을 그대로 쓰면 내용 중복 검증기에 걸린다. 로그 구성을 바꿔 다른 문제로 만든다.
    raw["logSamples"] = raw["logSamples"][:1]
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


def test_외부_생성_후보도_같은_필터를_거친다(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    good = valid_candidate()
    good["name"] = "monitor-ingested-good"
    (raw / "a.json").write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")
    broken = valid_candidate()
    broken["name"] = "monitor-ingested-broken"
    broken["alert"]["alertname"] = "MadeUpAlert"
    (raw / "b.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")

    pipeline = make_pipeline(tmp_path / "out", StubScreener(contradiction=False))
    saved = pipeline.ingest(sorted(raw.glob("*.json")), on_progress=lambda _: None)

    assert len(saved) == 1
    assert saved[0].name == "monitor-ingested-good.json"
    assert pipeline.stats.dropped_by["alert"] == 1


def test_읽을_수_없는_후보는_통계에_남는다(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "bad.json").write_text("not json", encoding="utf-8")

    pipeline = make_pipeline(tmp_path / "out", StubScreener(contradiction=False))
    saved = pipeline.ingest(sorted(raw.glob("*.json")), on_progress=lambda _: None)

    assert saved == []
    assert pipeline.stats.dropped_by["generation"] == 1
