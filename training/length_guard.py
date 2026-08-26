"""학습 샘플의 토큰 길이 검사.

**긴 샘플을 버리지 않는다.** 100건짜리 데이터에서 70건을 버리는 것은 선택지가 아니고,
데이터를 짧게 깎는 것은 더 나쁘다. 평가 시나리오도 같은 길이 분포를 가지므로, 학습만 짧게
맞추면 짧은 입력으로 배우고 긴 입력으로 시험 보는 상태가 된다.

그래서 이 검사는 필터가 아니라 **빌드를 멈추는 가드**다. 샘플이 설정된 최대 길이를 넘으면
설정을 올리라고 알리고 실패한다. 예산을 데이터에 맞추는 것이 맞는 방향이고, 메모리가 모자라면
배치 크기를 줄여서라도 길이를 확보한다.

2026-08-26에 학습 샘플 100건 중 70건이 조용히 잘린 채 학습됐다. 잘리는 쪽이 뒤쪽이고
응답 JSON의 마지막 필드가 evidenceLine이라, 하필 가르치려던 그 필드가 사라졌다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class SampleTooLongError(RuntimeError):
    pass


@dataclass(frozen=True)
class LengthReport:
    total: int
    longest: int
    over_limit: int
    limit: int

    @property
    def ok(self) -> bool:
        return self.over_limit == 0

    def recommended_limit(self) -> int:
        """가장 긴 샘플을 덮는 128의 배수."""
        return ((self.longest + 127) // 128) * 128


def measure(data_dir: Path, tokenizer, limit: int) -> LengthReport:
    lengths = []
    for split in ("train", "valid"):
        path = data_dir / f"{split}.jsonl"
        if not path.exists():
            continue
        for line in path.open(encoding="utf-8"):
            messages = json.loads(line)["messages"]
            lengths.append(len(tokenizer.apply_chat_template(messages, add_generation_prompt=False)))
    if not lengths:
        raise FileNotFoundError(f"학습 파일이 없다: {data_dir}")
    return LengthReport(
        total=len(lengths), longest=max(lengths),
        over_limit=sum(1 for n in lengths if n > limit), limit=limit)


def enforce(data_dir: Path, tokenizer, limit: int) -> LengthReport:
    report = measure(data_dir, tokenizer, limit)
    if not report.ok:
        raise SampleTooLongError(
            f"{report.total}건 중 {report.over_limit}건이 max_seq_length {limit}을 넘는다"
            f"(최장 {report.longest}). 샘플을 버리거나 깎지 말고 --max-seq-length를"
            f" {report.recommended_limit()} 이상으로 올려라. 메모리가 모자라면 배치 크기를 줄인다.")
    return report
