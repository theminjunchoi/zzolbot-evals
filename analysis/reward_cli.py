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
from dataclasses import dataclass, field
from pathlib import Path

from analysis.reward import RewardFunction, RewardSpec
from harness.analyzer import PROMPT_VARIANTS, build_prompt, parse_analysis
from harness.domain import Scenario
from harness.grounding import GroundingPipeline
from harness.loading import ScenarioLoader
from harness.local_model import extract_json
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
    # 시나리오별 샘플 점수 전체. 최고값만 남기면 "8번 중 몇 번 맞았나"를 알 수 없고,
    # 그러면 잠재 능력과 동전 던지기를 구별하지 못한다.
    samples: dict[str, list[float]] = field(default_factory=dict)

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
    """운영 경로와 같은 순서로 처리한다.

    extract_json을 거치지 않으면 코드 펜스로 감싼 출력이 전부 파싱 실패가 된다. 학습 전
    모델은 거의 항상 펜스를 붙이므로, 이걸 빼먹으면 33종 중 18종이 실패로 잡힌다(실제로 겪음).
    """
    try:
        analysis = parse_analysis(extract_json(text))
    except Exception:  # noqa: BLE001 - 파싱 실패도 결과의 일부다
        return reward.score(scenario, None), None
    return reward.score(scenario, analysis), analysis


def run_gemini_arm(label: str, model: str, scenarios: list[Scenario], variant: str,
                   reward: RewardFunction, min_interval: float) -> ArmResult:
    """참조 시스템(Gemini)을 같은 보상으로 잰다.

    주 종점을 참조 시스템에서 계산할 수 없으면 우리 점수가 좋은지 나쁜지 말할 수 없다.
    로컬 팔과 달리 샘플링은 하지 않는다(비용, 그리고 상한 추정은 로컬만 필요하다).
    """
    import os

    from harness.llm import GeminiJsonClient

    client = GeminiJsonClient(api_key=os.environ["GEMINI_ZZOL_BOT_API_KEY"],
                              model=model, min_interval_s=min_interval)
    grounding = GroundingPipeline()
    system = PROMPT_VARIANTS[variant]
    greedy: dict[str, float] = {}
    parse_failures = citation_pass = false_positives = 0
    positives = sum(1 for s in scenarios if expects_evidence(s))

    for i, scenario in enumerate(scenarios, 1):
        raw = client.generate_json(system, build_prompt(scenario))
        score, analysis = _score_one(reward, scenario, raw)
        greedy[scenario.name] = score.clamped
        if score.parse_failed:
            parse_failures += 1
        if analysis is not None:
            settled = grounding.apply(analysis, scenario)
            if expects_evidence(scenario) and settled.grounded:
                citation_pass += 1
            if not expects_evidence(scenario) and settled.grounded:
                false_positives += 1
        print(f"  [{label}] {i}/{len(scenarios)} {scenario.name} {greedy[scenario.name]:.2f}",
              flush=True)

    return ArmResult(label, greedy, dict(greedy), parse_failures, citation_pass,
                     false_positives, positives, len(scenarios) - positives, {})


def run_arm(label: str, adapter: str, scenarios: list[Scenario], model_path: str,
            variant: str, samples: int, temp: float, batch: int,
            reward: RewardFunction, constrained: bool = False,
            engine_kind: str = "mlx") -> ArmResult:
    """엔진만 갈아끼우고 **채점 경로는 한 벌만 쓴다.**

    프롬프트 조립, JSON 추출, 보상, 접지가 공유되어야 두 엔진의 차이가 나왔을 때
    엔진으로 원인이 좁혀진다. 여기서 갈라지면 대조가 무의미해진다.
    """
    from harness.engines import make_engine

    engine = make_engine(engine_kind, model_path, adapter or None)
    grounding = GroundingPipeline()
    system = PROMPT_VARIANTS[variant]

    greedy: dict[str, float] = {}
    best: dict[str, float] = {}
    per_sample: dict[str, list[float]] = {}
    parse_failures = citation_pass = false_positives = 0
    positives = sum(1 for s in scenarios if expects_evidence(s))

    for i, scenario in enumerate(scenarios, 1):
        user_prompt = build_prompt(scenario)
        logs = list(scenario.log_samples) if constrained else None
        raw = engine.generate(system, user_prompt, log_samples=logs, temp=0.0)[0]
        score, analysis = _score_one(reward, scenario, raw)
        greedy[scenario.name] = score.clamped
        if score.parse_failed:
            parse_failures += 1
        if analysis is not None:
            # 인용 통과와 오탐은 기존 리포트와 같은 정의를 쓴다. 접지 파이프라인을 거친 뒤의
            # grounded로 세지 않으면 과거 수치와 비교가 끊긴다.
            settled = grounding.apply(analysis, scenario)
            if expects_evidence(scenario) and settled.grounded:
                citation_pass += 1
            if not expects_evidence(scenario) and settled.grounded:
                false_positives += 1

        if samples > 1:
            outs = []
            for start in range(0, samples, batch):
                chunk = min(batch, samples - start)
                outs.extend(engine.generate(system, user_prompt, temp=temp, n=chunk))
            sample_scores = [_score_one(reward, scenario, t)[0].clamped for t in outs]
            per_sample[scenario.name] = sample_scores
            best[scenario.name] = max([greedy[scenario.name]] + sample_scores)
        else:
            best[scenario.name] = greedy[scenario.name]
        print(f"  [{label}] {i}/{len(scenarios)} {scenario.name} "
              f"그리디 {greedy[scenario.name]:.2f} 최고 {best[scenario.name]:.2f}", flush=True)

    return ArmResult(label, greedy, best, parse_failures, citation_pass,
                     false_positives, positives, len(scenarios) - positives, per_sample)


def main() -> int:
    parser = argparse.ArgumentParser(description="검증 가능한 보상 측정")
    parser.add_argument("--label", required=True)
    parser.add_argument("--arm", action="append", type=parse_arm, default=[],
                        help="이름=어댑터경로. 어댑터가 비면 베이스 모델")
    parser.add_argument("--scenarios-dir", type=Path, default=Path("golden-set/monitor"))
    parser.add_argument("--out-dir", type=Path, default=Path("reports/runs"))
    parser.add_argument("--local-model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-variant", default="production", choices=sorted(PROMPT_VARIANTS))
    parser.add_argument("--samples", type=int, default=1, help="1이면 그리디만, n>1이면 best-of-n")
    parser.add_argument("--temp", type=float, default=0.8)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--gemini", default="", metavar="MODEL",
                        help="참조 시스템을 이 모델로 함께 측정 (예: gemini-2.5-flash)")
    parser.add_argument("--min-interval", type=float, default=1.2)
    parser.add_argument("--constrained", action="store_true",
                        help="인용 필드를 실제 로그 줄로만 생성하도록 제약")
    parser.add_argument("--engine", default="mlx", choices=("mlx", "torch"),
                        help="생성 엔진(연산 프레임워크). torch는 fp16 비양자화만 된다"
                             " - bitsandbytes에 MPS 지원이 없다")
    parser.add_argument("--specificity", type=float, default=0.0,
                        help="구체성 배점. 사전 등록 검사 미통과로 기본 0")
    args = parser.parse_args()

    scenarios = ScenarioLoader().load_dir(args.scenarios_dir)
    spec = RewardSpec() if args.specificity == 0.0 else RewardSpec(specificity=args.specificity)
    reward = RewardFunction(spec)

    results = []
    if args.gemini:
        print(f"[gemini] 실행 중 ({args.gemini})", flush=True)
        results.append(run_gemini_arm("gemini", args.gemini, scenarios,
                                      args.prompt_variant, reward, args.min_interval))
    for name, adapter in args.arm:
        print(f"[{name}] 실행 중 (어댑터: {adapter or '없음'})", flush=True)
        results.append(run_arm(name, adapter, scenarios, args.local_model,
                               args.prompt_variant, args.samples, args.temp,
                               args.batch, reward, args.constrained, args.engine))

    lines = [
        f"# 보상 측정: {args.label}",
        "",
        f"- 시나리오 {len(scenarios)}종 (근거 있음 {results[0].positives} / 없음 {results[0].negatives})",
        f"- 엔진 {args.engine}, 모델 {args.local_model}, 프롬프트 {args.prompt_variant}, judge 미사용",
        f"- 배점 schema {spec.schema} / verdict {spec.verdict} / citation {spec.citation}"
        f" / specificity {spec.specificity}",
        f"- best-of-n: n={args.samples}, temperature={args.temp}",
        f"- 인용 제약 디코딩: {'적용' if args.constrained else '없음'}",
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
        json.dumps({r.label: {"greedy": r.greedy, "best": r.best, "samples": r.samples}
                    for r in results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
