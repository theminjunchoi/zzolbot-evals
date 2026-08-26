"""학습 데이터 빌드 진입점.

시나리오마다 교사(Gemini)에게 분석을 받고, 검증을 통과한 것만 학습 샘플로 채택한다.
탈락 사유는 전부 통계로 남긴다.

사용 예:
    python -m training.build_cli --label train-v1 --scenarios-dir candidates/train-v1
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

from harness.analyzer import PromptedAnalyzer
from harness.llm import GeminiJsonClient
from harness.loading import ScenarioLoader
from training.dataset import build_sample, repair_citation
from training.verification import verify_target

KEY_ENV = "GEMINI_ZZOL_BOT_API_KEY"


def main() -> int:
    parser = argparse.ArgumentParser(description="학습 데이터 빌드")
    parser.add_argument("--label", required=True)
    parser.add_argument("--scenarios-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("training/data"))
    parser.add_argument("--model", default="gemini-2.5-flash", help="교사 모델")
    parser.add_argument("--min-interval", type=float, default=1.5)
    parser.add_argument("--valid-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--retries", type=int, default=1, help="검증 실패 시 교사 재시도 횟수")
    args = parser.parse_args()

    api_key = os.environ.get(KEY_ENV, "")
    if not api_key:
        print(f"환경변수 {KEY_ENV}가 필요하다.", file=sys.stderr)
        return 1

    scenarios = ScenarioLoader().load_dir(args.scenarios_dir)
    analyzer = PromptedAnalyzer(GeminiJsonClient(
        api_key=api_key, model=args.model, min_interval_s=args.min_interval))

    samples, dropped = [], Counter()
    detail = []
    for scenario in scenarios:
        accepted = None
        for attempt in range(args.retries + 1):
            try:
                analysis = repair_citation(analyzer.analyze(scenario), scenario)
            except Exception as e:  # noqa: BLE001 - 교사 실패도 통계로 남긴다
                dropped["teacher"] += 1
                detail.append((scenario.name, "teacher", str(e)[:120]))
                break
            failures = verify_target(scenario, analysis)
            reasons = [r for rs in failures.values() for r in rs]
            if not reasons:
                accepted = analysis
                break
            if attempt == args.retries:
                rule = next(k for k, v in failures.items() if v)
                dropped[rule] += 1
                detail.append((scenario.name, rule, reasons[0][:120]))
        if accepted is not None:
            samples.append(build_sample(scenario, accepted))
            print(f"[KEEP] {scenario.name}")
        else:
            print(f"[DROP] {scenario.name}")

    if not samples:
        print("채택된 샘플이 없다.", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    rng.shuffle(samples)
    split = max(1, int(len(samples) * args.valid_ratio))
    valid, train = samples[:split], samples[split:]

    data_dir = args.out_dir / args.label
    data_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("valid", valid)):
        with (data_dir / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for sample in rows:
                f.write(json.dumps(sample.to_chat(), ensure_ascii=False) + "\n")

    lines = [
        f"# 학습 데이터 빌드: {args.label}",
        "",
        f"- 교사 모델: {args.model}",
        f"- 시나리오 {len(scenarios)}건 중 채택 {len(samples)}건 ({100.0 * len(samples) / len(scenarios):.0f}%)",
        f"- train {len(train)} / valid {len(valid)}",
        "",
        "| 탈락 사유 | 건수 |",
        "|---|---|",
    ]
    for rule, count in dropped.most_common():
        lines.append(f"| {rule} | {count} |")
    lines.extend(["", "### 탈락 상세", ""])
    for name, rule, reason in detail:
        lines.append(f"- `{name}` [{rule}] {reason}")
    (args.out_dir / f"{args.label}-build.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n채택 {len(samples)}/{len(scenarios)} → {data_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
