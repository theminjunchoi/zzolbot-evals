"""사전 등록 종점 측정 진입점.

여러 어댑터를 한 번에 돌려 인용 통과와 오탐을 짝지어 비교한다. judge를 부르지 않으므로
API 호출이 0이고, 로컬 분석기가 temperature 0이라 결과는 결정적이다.

사용 예:
    python -m analysis.endpoints_cli --label round2 \
        --arm base= --arm v2=training/adapters/sft-v2-s1 --arm v3=training/adapters/sft-v3-s1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from analysis.endpoints import EndpointRunner, paired_counts, two_sided_binomial
from harness.analyzer import PROMPT_VARIANTS, PromptedAnalyzer
from harness.loading import ScenarioLoader
from harness.local_model import MlxJsonClient

DEFAULT_MODEL = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"


def parse_arm(raw: str) -> tuple[str, str]:
    name, _, adapter = raw.partition("=")
    if not name:
        raise argparse.ArgumentTypeError(f"팔 이름이 비었다: {raw}")
    return name, adapter


def main() -> int:
    parser = argparse.ArgumentParser(description="사전 등록 종점(인용 통과/오탐) 측정")
    parser.add_argument("--label", required=True)
    parser.add_argument("--arm", action="append", type=parse_arm, required=True,
                        help="이름=어댑터경로. 어댑터가 비면 베이스 모델")
    parser.add_argument("--scenarios-dir", type=Path, default=Path("golden-set/monitor"))
    parser.add_argument("--out-dir", type=Path, default=Path("reports"))
    parser.add_argument("--local-model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-variant", default="production", choices=sorted(PROMPT_VARIANTS))
    args = parser.parse_args()

    scenarios = ScenarioLoader().load_dir(args.scenarios_dir)
    reports = {}
    for name, adapter in args.arm:
        client = MlxJsonClient(model_path=args.local_model, adapter_path=adapter or None)
        runner = EndpointRunner(PromptedAnalyzer(client, PROMPT_VARIANTS[args.prompt_variant]))
        print(f"[{name}] 실행 중 (어댑터: {adapter or '없음'})", flush=True)
        reports[name] = runner.run(name, scenarios)

    first = next(iter(reports.values()))
    n_pos, n_neg = len(first.positives), len(first.negatives)

    lines = [
        f"# 종점 측정: {args.label}",
        "",
        f"- 시나리오 {len(scenarios)}종 (근거 있음 {n_pos} / 근거 없음 {n_neg})",
        f"- 모델 {args.local_model}, 프롬프트 {args.prompt_variant}, judge 미사용",
        "",
        "| 팔 | 인용 통과 | 근거 주장 | 오탐 | 파싱 실패 |",
        "|---|---|---|---|---|",
    ]
    for name, report in reports.items():
        fp = report.false_positives
        lines.append(
            f"| {name} | {report.citation_pass}/{n_pos} | {report.claimed_on_positives}/{n_pos} "
            f"| {fp}/{n_neg} ({100.0 * fp / n_neg:.0f}%) | {report.parse_failures} |")

    names = [n for n, _ in args.arm]
    if len(names) >= 2:
        lines.extend(["", "## 짝지은 비교", "", "| 비교 | 지표 | 개선 | 악화 | p |", "|---|---|---|---|---|"])
        base = names[0]
        for other in names[1:]:
            for endpoint, only_pos in (("인용 통과", True), ("오탐 감소", False)):
                b, w, _ = paired_counts(reports[base], reports[other], only_pos)
                p = two_sided_binomial(b, w)
                lines.append(f"| {base} → {other} | {endpoint} | {b} | {w} | {p:.4f} |")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / f"{args.label}-endpoints.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.out_dir / f"{args.label}-endpoints.json").write_text(
        json.dumps({n: r.as_dict() for n, r in reports.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
