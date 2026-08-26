"""judge 캘리브레이션 진입점.

사용 예:
    python -m analysis.cli --label judge-cal-v1 --scenarios 10
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

from analysis.calibration import CalibrationReport, CalibrationRunner
from analysis.mutations import MUTATION_SETS, build_probes
from harness.judge import JUDGE_VARIANTS, GeminiJudge
from harness.llm import GeminiJsonClient
from harness.loading import ScenarioLoader

KEY_ENV = "GEMINI_ZZOL_BOT_API_KEY"


def load_passing_answers(reports_dir: Path) -> dict[str, str]:
    """시나리오별로 PASS 판정을 받은 답변 하나씩. 프로브의 원본이 된다."""
    answers: dict[str, str] = {}
    for path in sorted(glob.glob(str(reports_dir / "*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            row = json.loads(line)
            # 같은 폴더에 캘리브레이션 출력(스키마가 다름)이 섞여 있으므로 평가 결과만 고른다.
            score = row.get("score")
            if not isinstance(score, dict) or score.get("verdict") != "PASS":
                continue
            if row["scenario_name"] not in answers:
                answers[row["scenario_name"]] = row["answer"]
    return answers


def pick_balanced(answers: dict[str, str], limit: int) -> list[str]:
    """근거 있음 답변과 근거 없음 답변을 고르게 뽑는다. 변형기마다 적용 가능한 쪽이 다르다."""
    yes = [name for name, answer in answers.items() if "근거 발견: 예" in answer]
    no = [name for name, answer in answers.items() if "근거 발견: 아니오" in answer]
    picked, half = [], max(1, limit // 2)
    picked.extend(sorted(yes)[:half])
    picked.extend(sorted(no)[:limit - len(picked)])
    return picked


def main() -> int:
    parser = argparse.ArgumentParser(description="judge 변별력 캘리브레이션")
    parser.add_argument("--label", required=True)
    parser.add_argument("--scenarios", type=int, default=10, help="프로브를 만들 시나리오 수")
    parser.add_argument("--golden-dir", type=Path, default=Path("golden-set/monitor"))
    parser.add_argument("--reports-dir", type=Path, default=Path("reports/runs"))
    parser.add_argument("--out-dir", type=Path, default=Path("reports/runs"))
    parser.add_argument("--model", default="gemini-2.5-flash", help="judge 모델. 실측과 같아야 한다")
    parser.add_argument("--min-interval", type=float, default=1.5)
    parser.add_argument("--judge-variant", default="production", choices=sorted(JUDGE_VARIANTS),
                        help="측정할 judge 프롬프트 변형")
    parser.add_argument("--mutations", default="all", choices=sorted(MUTATION_SETS),
                        help="gross=명백한 오답(하한 측정), subtle=경계 영역(정밀도 측정)")
    args = parser.parse_args()

    api_key = os.environ.get(KEY_ENV, "")
    if not api_key:
        print(f"환경변수 {KEY_ENV}가 필요합니다.", file=sys.stderr)
        return 1

    scenarios = {s.name: s for s in ScenarioLoader().load_dir(args.golden_dir)}
    answers = load_passing_answers(args.reports_dir)
    names = pick_balanced({n: a for n, a in answers.items() if n in scenarios}, args.scenarios)

    probes = []
    for name in names:
        probes.extend(build_probes(name, answers[name], MUTATION_SETS[args.mutations],
                                   rubric=scenarios[name].rubric))
    if not probes:
        print("프로브를 만들 수 없습니다. 먼저 평가를 실행해 결과를 쌓으세요.", file=sys.stderr)
        return 1

    client = GeminiJsonClient(api_key=api_key, model=args.model, min_interval_s=args.min_interval)

    def on_result(result):
        mark = "OK " if result.agreed else "DIFF"
        print(f"[{mark}] {result.probe.scenario_name} [{result.probe.mutation}] "
              f"기대={result.probe.expected_verdict} judge={result.judge_verdict}")

    results = CalibrationRunner(GeminiJudge(client, JUDGE_VARIANTS[args.judge_variant]), on_result=on_result).run(scenarios, probes)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.out_dir / f"{args.label}.jsonl"
    with raw_path.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps({
                "scenario_name": result.probe.scenario_name,
                "mutation": result.probe.mutation,
                "expected_verdict": result.probe.expected_verdict,
                "judge_verdict": result.judge_verdict,
                "rationale": result.rationale,
                "answer": result.probe.answer,
            }, ensure_ascii=False) + "\n")

    report = CalibrationReport().to_markdown(args.label, args.model, results)
    report_path = args.out_dir / f"{args.label}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n리포트: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
