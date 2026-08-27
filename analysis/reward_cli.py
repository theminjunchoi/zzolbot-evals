"""보상 측정 진입점.

두 가지를 잰다.
- 그리디(temperature 0) 평균 보상: 각 팔의 현재 실력
- Best-of-n 최고 보상: 샘플링으로 도달 가능한 상한. RL로 얻을 여지가 있는지의 게이트

judge를 부르지 않으므로 API 비용이 0이다.

사용 예:
    python -m analysis.reward_cli --label headroom --arm base= --arm v4=training/adapters/sft-v4-s1
    python -m analysis.reward_cli --label bon --arm v4=training/adapters/sft-v4-s1 --samples 8
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from analysis.reward import RewardFunction, RewardSpec
from harness.analyzer import PROMPT_VARIANTS, build_prompt, parse_analysis
from harness.domain import Scenario
from harness.loading import ScenarioLoader
from training.verification import expects_evidence

DEFAULT_MODEL = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"


@dataclass(frozen=True)
class ArmResult:
    label: str
    greedy: dict[str, float]
    best: dict[str, float]
    parse_failures: int
    citation_pass: int
    false_positives: int
    positives: int
    negatives: int

    @property
    def greedy_mean(self) -> float:
        return statistics.fmean(self.greedy.values())

    @property
    def best_mean(self) -> float:
        return statistics.fmean(self.best.values())


def parse_arm(raw: str) -> tuple[str, str]:
    name, _, adapter = raw.partition("=")
    if not name:
        raise argparse.ArgumentTypeError(f"팔 이름이 비었다: {raw}")
    return name, adapter


def _score_one(reward: RewardFunction, scenario: Scenario, text: str):
    try:
        analysis = parse_analysis(text)
    except Exception:  # noqa: BLE001 - 파싱 실패도 결과의 일부다
        return reward.score(scenario, None), None
    return reward.score(scenario, analysis), analysis


def run_arm(label: str, adapter: str, scenarios: list[Scenario], model_path: str,
            variant: str, samples: int, temp: float, batch: int,
            reward: RewardFunction) -> ArmResult:
    from mlx_lm import batch_generate, generate, load
    from mlx_lm.sample_utils import make_sampler

    model, tok = load(model_path, adapter_path=adapter or None)
    system = PROMPT_VARIANTS[variant]
    greedy_sampler = make_sampler(temp=0.0)
    warm_sampler = make_sampler(temp=temp, top_p=0.95)

    greedy: dict[str, float] = {}
    best: dict[str, float] = {}
    parse_failures = citation_pass = false_positives = 0
    positives = sum(1 for s in scenarios if expects_evidence(s))

    for i, scenario in enumerate(scenarios, 1):
        text_prompt = tok.apply_chat_template(
            [{"role": "system", "content": system},
             {"role": "user", "content": build_prompt(scenario)}],
            tokenize=False, add_generation_prompt=True)

        raw = generate(model, tok, text_prompt, max_tokens=700,
                       sampler=greedy_sampler, verbose=False)
        score, analysis = _score_one(reward, scenario, raw)
        greedy[scenario.name] = score.clamped
        if score.parse_failed:
            parse_failures += 1
        if analysis is not None:
            grounded = score.parts.get("citation", 0.0) > 0.0 and analysis.evidence_found
            if expects_evidence(scenario) and grounded:
                citation_pass += 1
            if not expects_evidence(scenario) and analysis.evidence_found:
                false_positives += 1

        if samples > 1:
            ids = [tok.encode(text_prompt)] * samples
            outs = []
            for start in range(0, samples, batch):
                outs.extend(batch_generate(model, tok, ids[start:start + batch],
                                           max_tokens=700, sampler=warm_sampler,
                                           verbose=False).texts)
            best[scenario.name] = max(
                [greedy[scenario.name]]
                + [_score_one(reward, scenario, t)[0].clamped for t in outs])
        else:
            best[scenario.name] = greedy[scenario.name]
        print(f"  [{label}] {i}/{len(scenarios)} {scenario.name} "
              f"그리디 {greedy[scenario.name]:.2f} 최고 {best[scenario.name]:.2f}", flush=True)

    return ArmResult(label, greedy, best, parse_failures, citation_pass,
                     false_positives, positives, len(scenarios) - positives)


def main() -> int:
    parser = argparse.ArgumentParser(description="검증 가능한 보상 측정")
    parser.add_argument("--label", required=True)
    parser.add_argument("--arm", action="append", type=parse_arm, required=True,
                        help="이름=어댑터경로. 어댑터가 비면 베이스 모델")
    parser.add_argument("--scenarios-dir", type=Path, default=Path("golden-set/monitor"))
    parser.add_argument("--out-dir", type=Path, default=Path("reports/runs"))
    parser.add_argument("--local-model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-variant", default="production", choices=sorted(PROMPT_VARIANTS))
    parser.add_argument("--samples", type=int, default=1, help="1이면 그리디만, n>1이면 best-of-n")
    parser.add_argument("--temp", type=float, default=0.8)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--specificity", type=float, default=0.0,
                        help="구체성 배점. 사전 등록 검사 미통과로 기본 0")
    args = parser.parse_args()

    scenarios = ScenarioLoader().load_dir(args.scenarios_dir)
    spec = RewardSpec() if args.specificity == 0.0 else RewardSpec(specificity=args.specificity)
    reward = RewardFunction(spec)

    results = []
    for name, adapter in args.arm:
        print(f"[{name}] 실행 중 (어댑터: {adapter or '없음'})", flush=True)
        results.append(run_arm(name, adapter, scenarios, args.local_model,
                               args.prompt_variant, args.samples, args.temp,
                               args.batch, reward))

    lines = [
        f"# 보상 측정: {args.label}",
        "",
        f"- 시나리오 {len(scenarios)}종 (근거 있음 {results[0].positives} / 없음 {results[0].negatives})",
        f"- 모델 {args.local_model}, 프롬프트 {args.prompt_variant}, judge 미사용",
        f"- 배점 schema {spec.schema} / verdict {spec.verdict} / citation {spec.citation}"
        f" / specificity {spec.specificity}",
        f"- best-of-n: n={args.samples}, temperature={args.temp}",
        "",
        "| 팔 | 그리디 평균 | 최고 평균 | 상한 여유 | 인용 통과 | 오탐 | 파싱 실패 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r.label} | {r.greedy_mean:.3f} | {r.best_mean:.3f} | "
            f"**+{r.best_mean - r.greedy_mean:.3f}** | {r.citation_pass}/{r.positives} | "
            f"{r.false_positives}/{r.negatives} | {r.parse_failures} |")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / f"{args.label}-reward.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.out_dir / f"{args.label}-reward.json").write_text(
        json.dumps({r.label: {"greedy": r.greedy, "best": r.best} for r in results},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
