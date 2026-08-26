"""외부 생성 후보를 검증 파이프라인에 넣는 진입점.

Claude 에이전트가 써둔 후보 JSON을 같은 rule 필터와 스크리너에 통과시킨다.
생성 주체만 다르고 품질 기준은 Gemini 생성 경로와 동일하다.

사용 예:
    python -m synthesis.ingest_cli --label train-v1 --input-dir raw/train-v1
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from harness.llm import GeminiJsonClient
from harness.loading import ScenarioLoader
from synthesis.pipeline import SynthesisPipeline
from synthesis.screening import LlmScreener

KEY_ENV = "GEMINI_ZZOL_BOT_API_KEY"


def main() -> int:
    parser = argparse.ArgumentParser(description="외부 생성 후보 검증 적재")
    parser.add_argument("--label", required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--golden-dir", type=Path, default=Path("golden-set/monitor"))
    parser.add_argument("--out-dir", type=Path, default=Path("candidates"))
    parser.add_argument("--screen-model", default="gemini-2.5-flash")
    parser.add_argument("--no-screen", action="store_true",
                        help="스크리닝을 끈다. 학습 데이터처럼 양이 많고 사람 검토를 생략하는 경우 비용을 보고 판단한다")
    parser.add_argument("--min-interval", type=float, default=1.5)
    parser.add_argument("--compare-dirs", nargs="*", type=Path, default=[],
                        help="중복 비교에 함께 넣을 기존 후보 디렉터리. 배치 사이 중복을 막는다")
    args = parser.parse_args()

    loader = ScenarioLoader()
    exemplars = loader.load_dir(args.golden_dir)
    previous = [s for d in args.compare_dirs if d.exists() for s in loader.load_dir(d)]
    existing = {s.name for s in exemplars} | {s.name for s in previous}

    screener = None
    if not args.no_screen:
        api_key = os.environ.get(KEY_ENV, "")
        if not api_key:
            print(f"스크리닝에는 {KEY_ENV}가 필요하다. 끄려면 --no-screen.", file=sys.stderr)
            return 1
        screener = LlmScreener(GeminiJsonClient(
            api_key=api_key, model=args.screen_model, min_interval_s=args.min_interval))

    pipeline = SynthesisPipeline(
        generator=None, exemplars=exemplars, existing_names=existing,
        out_dir=args.out_dir / args.label, screener=screener, dedup_against=previous)
    paths = sorted(args.input_dir.glob("*.json"))
    if not paths:
        print(f"입력 후보가 없다: {args.input_dir}", file=sys.stderr)
        return 1
    saved = pipeline.ingest(paths)

    stats_path = args.out_dir / f"{args.label}-stats.md"
    stats_path.write_text(pipeline.stats_markdown(), encoding="utf-8")
    print(f"\n생존 {len(saved)}/{len(paths)} → {args.out_dir / args.label}")
    print(f"통계: {stats_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
