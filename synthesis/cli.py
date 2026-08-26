"""합성 파이프라인 진입점.

사용 예:
    python -m synthesis.cli --label gen-v1 --per-axis 2 --min-interval 2
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path

from harness.llm import GeminiJsonClient
from harness.loading import ScenarioLoader
from synthesis.axes import AXES
from synthesis.generator import ScenarioGenerator
from synthesis.pipeline import BatchItem, SynthesisPipeline
from synthesis.screening import LlmScreener

KEY_ENV = "GEMINI_ZZOL_BOT_API_KEY"

# 합성 경로의 샘플링 기본값. 평가 경로(GeminiJsonClient 기본값 0.0)와 반드시 달라야 한다.
DEFAULT_TEMPERATURE = 0.9
DEFAULT_TOP_P = 0.95

# 축별로 어울리는 알림 후보. 배치 구성 시 여기서 순환 선택한다.
AXIS_ALERTS: dict[str, list[str]] = {
    "positive-dense": ["AppErrorLogSpike", "Http5xxRatioHigh", "RedisStreamBacklogHigh",
                       "OutboxDeadLetterHigh", "RedisStreamE2eLatencyHigh", "CircuitBreakerOpen"],
    "unrelated-trap": ["DbConnectionPoolHigh", "JvmHeapUsageHigh", "LoginSuccessDroppedToZero",
                       "DiskUsageHigh", "WsConnectionFailuresHigh", "ErrorBudgetBurnSlow"],
    "stale-reingested": ["AppErrorLogSpike"],
    "sparse-evidence": ["AppErrorLogSpike", "Http5xxRatioHigh", "WsInboundLatencyHigh"],
    "partial-relevance": ["Http5xxRatioHigh", "AppErrorLogSpike", "RedisStreamE2eLatencyHigh"],
    "compound-cause": ["Http5xxRatioHigh", "AppErrorLogSpike", "RedisStreamE2eLatencyHigh"],
    "near-miss-component": ["DbConnectionPoolHigh", "RedisStreamBacklogHigh", "OutboxDeadLetterHigh",
                            "JvmHeapUsageHigh"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="골든 시나리오 합성 파이프라인")
    parser.add_argument("--label", required=True)
    parser.add_argument("--per-axis", type=int, default=2, help="축당 생성 시도 수")
    parser.add_argument("--axes", nargs="*", default=list(AXES), help="생성할 축 (기본 전체)")
    parser.add_argument("--golden-dir", type=Path, default=Path("golden-set/monitor"))
    parser.add_argument("--out-dir", type=Path, default=Path("candidates"))
    parser.add_argument("--min-interval", type=float, default=6.5)
    parser.add_argument("--model", default="gemini-3.1-flash-lite",
                        help="생성 모델. 피평가 모델(gemini-2.5-flash)과 분리해 자기 생성 편향을 줄인다")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE,
                        help="생성 다양성. 평가 경로와 달리 결정적 디코딩을 쓰면 복제본이 나온다")
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P,
                        help="생성 다양성. temperature만 올리고 top_p를 0으로 두면 여전히 greedy에 가깝다")
    parser.add_argument("--seed", type=int, default=20260826, help="알림 순환 선택 시드")
    parser.add_argument("--screen-model", default="gemini-2.5-flash",
                        help="정합성 스크리너 모델. 판정이 아니라 rubric-로그 모순만 본다")
    parser.add_argument("--no-screen", action="store_true", help="스크리닝 단계를 끈다")
    args = parser.parse_args()

    api_key = os.environ.get(KEY_ENV, "")
    if not api_key:
        print(f"환경변수 {KEY_ENV}가 필요합니다.", file=sys.stderr)
        return 1

    exemplars = ScenarioLoader().load_dir(args.golden_dir)
    existing_names = {s.name for s in exemplars}
    rng = random.Random(args.seed)

    batch = []
    for axis_key in args.axes:
        axis = AXES[axis_key]
        alerts = AXIS_ALERTS.get(axis_key, ["AppErrorLogSpike"])
        for i in range(args.per_axis):
            batch.append(BatchItem(axis, alerts[(i + rng.randrange(len(alerts))) % len(alerts)], 1))

    client = GeminiJsonClient(
        api_key=api_key, model=args.model, min_interval_s=args.min_interval,
        temperature=args.temperature, top_p=args.top_p)
    screener = None if args.no_screen else LlmScreener(
        GeminiJsonClient(api_key=api_key, model=args.screen_model, min_interval_s=args.min_interval))
    pipeline = SynthesisPipeline(
        ScenarioGenerator(client), exemplars, existing_names, args.out_dir / args.label,
        screener=screener)
    saved = pipeline.run(batch)

    stats_path = args.out_dir / f"{args.label}-stats.md"
    stats_path.write_text(pipeline.stats_markdown(), encoding="utf-8")
    print(f"\n생존 {len(saved)}건 → {args.out_dir / args.label}")
    print(f"통계: {stats_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
