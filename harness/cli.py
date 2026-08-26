"""명령행 진입점. 조립(와이어링)만 담당한다.

사용 예:
    python -m harness.cli --label baseline --repeats 3
    python -m harness.cli --label smoke --limit 2
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from harness.analyzer import PROMPT_VARIANTS, GeminiAnalyzer
from harness.judge import GeminiJudge
from harness.llm import GeminiJsonClient
from harness.loading import ScenarioLoader
from harness.reporting import JsonlSink, ReportBuilder
from harness.runner import EvalRunner
from harness.splits import ALL, SplitManifest

DEFAULT_MODEL = "gemini-2.5-flash"
KEY_ENV = "GEMINI_ZZOL_BOT_API_KEY"


def main() -> int:
    parser = argparse.ArgumentParser(description="zzolbot monitor 골든셋 평가 하네스")
    parser.add_argument("--label", required=True, help="실행 라벨 (리포트 파일명에 사용)")
    parser.add_argument("--scenarios-dir", type=Path, default=Path("golden-set/monitor"))
    parser.add_argument("--repeats", type=int, default=1, help="시나리오당 독립 시행 수")
    parser.add_argument("--limit", type=int, default=0, help="앞에서 N개 시나리오만 (0=전체)")
    parser.add_argument("--split", default=ALL,
                        help="평가할 분할. 개선 실험은 dev, 최종 보고 숫자는 test에서 낸다")
    parser.add_argument("--splits-file", type=Path, default=Path("golden-set/splits.json"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-variant", default="production", choices=sorted(PROMPT_VARIANTS),
                        help="분석기 프롬프트 변형. production은 팀 레포와 동일한 운영 프롬프트다")
    parser.add_argument("--min-interval", type=float, default=6.5,
                        help="LLM 호출 간 최소 간격(초). 무료 티어는 6.5 권장, 유료 티어는 1~2로 단축 가능")
    parser.add_argument("--out-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    api_key = os.environ.get(KEY_ENV, "")
    if not api_key:
        print(f"환경변수 {KEY_ENV}가 필요합니다.", file=sys.stderr)
        return 1

    scenarios = ScenarioLoader().load_dir(args.scenarios_dir)
    if args.split != ALL:
        scenarios = SplitManifest.load(args.splits_file).filter(scenarios, args.split)
        if not scenarios:
            print(f"분할 {args.split}에 해당하는 시나리오가 없습니다.", file=sys.stderr)
            return 1
    if args.limit:
        scenarios = scenarios[: args.limit]

    client = GeminiJsonClient(api_key=api_key, model=args.model, min_interval_s=args.min_interval)
    sink = JsonlSink(args.out_dir / f"{args.label}.jsonl")

    def on_result(result):
        sink.write(result)
        mark = "PASS" if result.score.passed else "FAIL"
        print(f"[{mark}] {result.scenario_name} trial={result.trial} "
              f"acc={result.score.accuracy} grd={result.score.groundedness}")

    runner = EvalRunner(
        analyzer=GeminiAnalyzer(client, PROMPT_VARIANTS[args.prompt_variant]),
        judge=GeminiJudge(client), on_result=on_result)
    results = runner.run(scenarios, repeats=args.repeats)

    builder = ReportBuilder()
    report = builder.to_markdown(args.label, args.model, builder.aggregate(results))
    report_path = args.out_dir / f"{args.label}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n리포트: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
