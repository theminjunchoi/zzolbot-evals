"""분할 계약. 모든 시나리오가 정확히 한 분할에 속해야 개선용과 보고용이 섞이지 않는다."""

import json
from pathlib import Path

import pytest

from harness.loading import ScenarioLoader
from harness.splits import ALL, SplitManifest

ROOT = Path(__file__).parent.parent
GOLDEN_DIR = ROOT / "golden-set" / "monitor"
SPLITS_FILE = ROOT / "golden-set" / "splits.json"


def test_모든_시나리오가_정확히_한_분할에_속한다():
    scenarios = {s.name for s in ScenarioLoader().load_dir(GOLDEN_DIR)}
    manifest = json.loads(SPLITS_FILE.read_text(encoding="utf-8"))
    dev, test = set(manifest["dev"]), set(manifest["test"])

    assert dev & test == set(), f"두 분할에 겹치는 시나리오: {dev & test}"
    assert dev | test == scenarios, f"배정 누락: {scenarios - (dev | test)}"


def test_test_분할은_비어_있지_않다():
    manifest = SplitManifest.load(SPLITS_FILE)

    assert len(manifest.members("test")) > 0


def test_분할로_시나리오를_거른다():
    scenarios = ScenarioLoader().load_dir(GOLDEN_DIR)
    manifest = SplitManifest.load(SPLITS_FILE)

    dev = manifest.filter(scenarios, "dev")
    test = manifest.filter(scenarios, "test")

    assert len(dev) + len(test) == len(scenarios)
    assert len(manifest.filter(scenarios, ALL)) == len(scenarios)


def test_알_수_없는_분할은_오류다():
    manifest = SplitManifest.load(SPLITS_FILE)

    with pytest.raises(KeyError):
        manifest.members("train")
