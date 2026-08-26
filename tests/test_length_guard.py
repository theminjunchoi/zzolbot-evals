"""길이 가드 계약. 데이터를 버리는 것이 아니라 설정을 올리도록 강제한다."""

import json

import pytest

from training.length_guard import SampleTooLongError, enforce, measure


class StubTokenizer:
    """메시지 글자 수를 토큰 수로 삼는 단순 대역."""

    def apply_chat_template(self, messages, add_generation_prompt=False):
        return list("".join(m["content"] for m in messages))


def write(tmp_path, lengths):
    for split, sizes in lengths.items():
        with (tmp_path / f"{split}.jsonl").open("w", encoding="utf-8") as f:
            for size in sizes:
                f.write(json.dumps({"messages": [
                    {"role": "system", "content": ""},
                    {"role": "user", "content": "a" * size},
                    {"role": "assistant", "content": ""},
                ]}) + "\n")
    return tmp_path


def test_모두_한도_안이면_통과한다(tmp_path):
    write(tmp_path, {"train": [100, 200], "valid": [150]})

    report = enforce(tmp_path, StubTokenizer(), limit=300)

    assert report.ok
    assert report.total == 3
    assert report.longest == 200


def test_한도를_넘으면_빌드를_멈춘다(tmp_path):
    write(tmp_path, {"train": [100, 500], "valid": [150]})

    with pytest.raises(SampleTooLongError) as e:
        enforce(tmp_path, StubTokenizer(), limit=300)

    assert "1건이 max_seq_length 300을 넘는다" in str(e.value)


def test_권장_한도는_최장_샘플을_덮는다(tmp_path):
    write(tmp_path, {"train": [3086]})

    report = measure(tmp_path, StubTokenizer(), limit=2048)

    assert report.over_limit == 1
    assert report.recommended_limit() >= 3086
    assert report.recommended_limit() % 128 == 0


def test_긴_샘플을_버리지_않는다(tmp_path):
    """가드는 필터가 아니다. 집계에 모든 샘플이 그대로 남아야 한다."""
    write(tmp_path, {"train": [100, 5000]})

    report = measure(tmp_path, StubTokenizer(), limit=300)

    assert report.total == 2
