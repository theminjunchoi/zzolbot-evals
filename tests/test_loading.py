from pathlib import Path

import pytest

from harness.loading import ScenarioLoader

GOLDEN_DIR = Path(__file__).parent.parent / "golden-set" / "monitor"


def test_실제_골든셋_20종을_전부_읽는다():
    scenarios = ScenarioLoader().load_dir(GOLDEN_DIR)

    assert len(scenarios) == 20
    names = {s.name for s in scenarios}
    assert "monitor-mass-ip-blocking-description-echo-trap" in names
    assert all(s.log_environment == "prod" for s in scenarios)
    assert all(s.log_samples for s in scenarios)
    assert all(s.alert.alertname for s in scenarios)


def test_필수_필드가_빠지면_즉시_실패한다(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text('{"name": "x", "question": "q"}', encoding="utf-8")

    with pytest.raises(ValueError, match="필수 필드 누락"):
        ScenarioLoader().load_file(broken)


def test_빈_디렉터리는_오류다(tmp_path):
    with pytest.raises(FileNotFoundError):
        ScenarioLoader().load_dir(tmp_path)
