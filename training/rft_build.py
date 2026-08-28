"""RFT 학습 데이터 빌드.

샘플링 결과에서 프롬프트마다 **보상이 가장 높은 것 하나**를 골라 학습 샘플로 만든다.
교사(API)를 부르지 않는다. 정답을 판정하는 것이 검증기이고, 후보를 만드는 것이 모델 자신이다.

만점 샘플 개수로 프롬프트를 거르지 않는다. 드물게 맞는 행동을 흔하게 만드는 것이 목적이라,
"이미 자주 맞히는 것만 쓴다"는 규칙은 고쳐야 할 것을 정확히 배제한다(계획서 A단계 참조).

다만 **최고 보상이 만점에 못 미치면 제외한다.** 틀린 것을 정답으로 가르치게 되기 때문이다.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

from harness.analyzer import SYSTEM_INSTRUCTION, build_prompt, parse_analysis
from harness.local_model import extract_json
from harness.loading import ScenarioLoader
from training.dataset import to_target_json


def main() -> int:
    parser = argparse.ArgumentParser(description="RFT 학습 데이터 빌드")
    parser.add_argument("--samples-dir", type=Path, required=True)
    parser.add_argument("--scenarios-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-reward", type=float, default=0.999,
                        help="이 값 미만이면 제외. 틀린 것을 정답으로 가르치지 않기 위함")
    parser.add_argument("--valid-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20260828)
    args = parser.parse_args()

    scenarios = {s.name: s for s in ScenarioLoader().load_dir(args.scenarios_dir)}
    stats = Counter()
    samples = []

    for path in sorted(args.samples_dir.glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        scenario = scenarios.get(row["scenario"])
        if scenario is None:
            stats["시나리오 없음"] += 1
            continue
        best = max(row["samples"] + [row["greedy"]], key=lambda s: s["total"])
        if best["total"] < args.min_reward:
            stats["최고 보상이 만점 미달"] += 1
            continue
        try:
            analysis = parse_analysis(extract_json(best["text"]))
        except Exception:  # noqa: BLE001
            stats["파싱 실패"] += 1
            continue
        # 모델 출력을 그대로 쓰지 않고 스키마로 재직렬화한다. 코드 펜스나 앞뒤 설명이
        # 학습 목표에 섞이면 그 습관까지 가르치게 된다.
        samples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": build_prompt(scenario)},
                {"role": "assistant", "content": to_target_json(analysis)},
            ],
            "_from_greedy": best is row["greedy"],
        })
        stats["채택"] += 1

    if not samples:
        print("채택된 샘플이 없다.", file=sys.stderr)
        return 1

    from_greedy = sum(1 for s in samples if s.pop("_from_greedy"))
    rng = random.Random(args.seed)
    rng.shuffle(samples)
    split = max(1, int(len(samples) * args.valid_ratio))
    valid, train = samples[:split], samples[split:]

    args.out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("valid", valid)):
        with (args.out / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"채택 {stats['채택']}건 → train {len(train)} / valid {len(valid)}")
    print(f"  그중 그리디가 최고였던 것: {from_greedy}건 (자기증류)")
    print(f"  샘플링이 그리디를 이긴 것: {stats['채택'] - from_greedy}건 (RFT의 실제 기여)")
    for reason, count in stats.most_common():
        if reason != "채택":
            print(f"  제외 [{reason}]: {count}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
