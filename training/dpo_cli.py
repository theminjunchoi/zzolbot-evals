"""DPO 학습 진입점.

선호 쌍을 만들고, 참조 로그 확률을 미리 계산하고, LoRA 어댑터를 DPO 손실로 학습한다.

chosen은 **교사 출력**이다. 자기 최고 샘플로 하면 모델이 한 번도 못 맞히는 프롬프트에서
chosen이 없어 가장 어려운 경계를 건너뛴다. C단계(RFT)가 그 함정으로 실패했다.

사용 예:
    python -m training.dpo_cli --label dpo-v1 \
      --samples-dir training/data/rft-v6-samples \
      --teacher-dir training/data/dpo-teacher \
      --scenarios-dir candidates/rft-prompts \
      --base-adapter training/adapters/sft-v6-s1 \
      --out training/adapters/dpo-v1-s1
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

from harness.analyzer import SYSTEM_INSTRUCTION, build_prompt
from harness.loading import ScenarioLoader
from training.dpo import PreferencePair, implicit_accuracy, precompute_reference, train_step
from training.verification import expects_evidence

DEFAULT_MODEL = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"


def build_pairs(samples_dir: Path, teacher: dict[str, str], scenarios, tokenizer,
                min_margin: float) -> tuple[list[PreferencePair], Counter, Counter]:
    """(프롬프트 토큰, chosen 토큰, rejected 토큰) 쌍을 만든다.

    버려지는 쌍이 한쪽 판정에 몰리는지도 함께 센다. RFT에서 필터가 비대칭으로 작동해
    판정 비율을 밀었고 그것이 실패 원인이었다. 같은 일을 다시 겪지 않으려면 세어야 한다.
    """
    stats, dropped_by_verdict = Counter(), Counter()
    pairs = []
    for path in sorted(samples_dir.glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        name = row["scenario"]
        scenario = scenarios.get(name)
        if scenario is None or name not in teacher:
            stats["교사 출력 없음"] += 1
            continue
        verdict = "예" if expects_evidence(scenario) else "아니오"

        worst = min(row["samples"] + [row["greedy"]], key=lambda s: s["total"])
        if 1.0 - worst["total"] < min_margin:
            stats["마진 부족"] += 1
            dropped_by_verdict[verdict] += 1
            continue

        prompt_text = tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM_INSTRUCTION},
             {"role": "user", "content": build_prompt(scenario)}],
            tokenize=False, add_generation_prompt=True)
        pairs.append(PreferencePair(
            prompt=tokenizer.encode(prompt_text),
            chosen=tokenizer.encode(teacher[name], add_special_tokens=False),
            rejected=tokenizer.encode(worst["text"], add_special_tokens=False)))
        stats["채택"] += 1
        stats[f"채택-{verdict}"] += 1
    return pairs, stats, dropped_by_verdict


def load_teacher(teacher_dir: Path, scenarios) -> dict[str, str]:
    """교사 출력을 시나리오 이름으로 찾을 수 있게 만든다.

    빌드된 jsonl에는 이름이 없고 프롬프트만 있으므로 프롬프트로 역인덱싱한다.
    """
    by_prompt = {}
    for split in ("train", "valid"):
        path = teacher_dir / f"{split}.jsonl"
        if not path.exists():
            continue
        for line in path.open(encoding="utf-8"):
            row = json.loads(line)
            by_prompt[row["messages"][1]["content"]] = row["messages"][-1]["content"]
    return {s.name: by_prompt[build_prompt(s)] for s in scenarios if build_prompt(s) in by_prompt}


def main() -> int:
    parser = argparse.ArgumentParser(description="DPO 학습")
    parser.add_argument("--label", required=True)
    parser.add_argument("--samples-dir", type=Path, required=True)
    parser.add_argument("--teacher-dir", type=Path, required=True)
    parser.add_argument("--scenarios-dir", type=Path, required=True)
    parser.add_argument("--base-adapter", type=Path, required=True,
                        help="출발 정책이자 참조 정책이 되는 SFT 어댑터")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--beta", type=float, default=0.1)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--min-margin", type=float, default=0.2)
    parser.add_argument("--max-skew", type=float, default=0.15,
                        help="채택 쌍의 예 비율이 원래 풀에서 이만큼 넘게 벗어나면 중단")
    parser.add_argument("--allow-skew", action="store_true",
                        help="편중을 알고도 진행. beta를 함께 올릴 것")
    parser.add_argument("--collapse-at", type=float, default=1e-3,
                        help="이 값 아래로 손실이 내려가면 과적합으로 보고 조기 종료")
    parser.add_argument("--seed", type=int, default=20260828)
    args = parser.parse_args()

    import mlx.core as mx
    import mlx.optimizers as optim
    from mlx_lm import load

    mx.random.seed(args.seed)
    scenarios = ScenarioLoader().load_dir(args.scenarios_dir)
    by_name = {s.name: s for s in scenarios}

    print("모델 적재 중 (참조 = SFT 어댑터)", flush=True)
    # mlx_lm.load는 어댑터를 얹지만 베이스를 동결하지 않는다. 그대로 학습하면 LoRA가
    # 아니라 전 레이어의 bias까지 갱신된다(실측 365 텐서). 학습 경로와 같은 순서로
    # 다시 구성한다: freeze() → linear_to_lora_layers() → 가중치 적재.
    from types import SimpleNamespace

    from mlx_lm.tuner.utils import linear_to_lora_layers

    model, tokenizer = load(args.model)
    cfg = SimpleNamespace(**json.loads(
        (args.base_adapter / "adapter_config.json").read_text(encoding="utf-8")))
    model.freeze()
    linear_to_lora_layers(model, cfg.num_layers, cfg.lora_parameters)
    model.load_weights(str(args.base_adapter / "adapters.safetensors"), strict=False)

    from mlx.utils import tree_flatten as _tf
    n_train = sum(v.size for _, v in _tf(model.trainable_parameters()))
    print(f"  학습 가능 파라미터 {n_train / 1e6:.2f}M (LoRA만)", flush=True)
    teacher = load_teacher(args.teacher_dir, scenarios)
    print(f"교사 출력 {len(teacher)}건 확보", flush=True)

    pairs, stats, dropped = build_pairs(args.samples_dir, teacher, by_name,
                                        tokenizer, args.min_margin)
    print(f"\n선호 쌍 {len(pairs)}개")
    print(f"  채택: 예 {stats['채택-예']} / 아니오 {stats['채택-아니오']}")
    for reason, count in stats.most_common():
        if not reason.startswith("채택"):
            print(f"  제외 [{reason}]: {count}건")
    if dropped:
        print(f"  제외된 것의 판정 분포: {dict(dropped)}")
    if not pairs:
        print("쌍이 없다.", file=sys.stderr)
        return 1

    # 가드 1: 판정 편중.
    # 사람이 로그를 읽고 판단하는 구조는 실제로 실패했다(2026-08-28: 88% 편중을 보고도
    # 학습을 돌려 오탐이 1/18에서 10/18이 됐다). 코드가 막는다.
    kept_yes = stats["채택-예"] / len(pairs)
    pool_yes = sum(1 for s in scenarios if expects_evidence(s)) / len(scenarios)
    skew = abs(kept_yes - pool_yes)
    print(f"\n판정 비율: 쌍 {kept_yes:.0%} 예 / 원래 풀 {pool_yes:.0%} 예 (편차 {skew:.0%})")
    if skew > args.max_skew and not args.allow_skew:
        print(f"중단: 편차가 {args.max_skew:.0%}를 넘는다. 학습하면 판정 성향이 그쪽으로 밀린다.",
              file=sys.stderr)
        print(f"       그래도 돌리려면 --allow-skew. 그 경우 beta를 올려 참조에서 멀어지지 "
              f"않게 하라 (현재 {args.beta}).", file=sys.stderr)
        return 2

    # 참조는 학습 전 정책이다. 어댑터를 이미 얹은 상태에서 계산하고 고정한다.
    print("\n참조 로그 확률 사전 계산 중", flush=True)
    started = time.time()
    pairs = precompute_reference(model, pairs)
    print(f"  {time.time() - started:.0f}초", flush=True)

    optimizer = optim.Adam(learning_rate=args.learning_rate)
    order = list(range(len(pairs)))
    step = 0
    collapsed = False
    for epoch in range(args.epochs):
        import random
        random.Random(args.seed + epoch).shuffle(order)
        losses = []
        for i in order:
            losses.append(train_step(model, optimizer, pairs[i], args.beta))
            step += 1
            if step % 10 == 0:
                recent = sum(losses[-10:]) / 10
                acc = sum(implicit_accuracy(model, pairs[j]) for j in order[:10]) / 10
                print(f"  step {step}  손실 {recent:.5f}  암묵 정확도 {acc:.2f}", flush=True)
                # 가드 2: 손실 붕괴. 쌍이 적을 때 참조에서 너무 멀어진 신호다.
                if recent < args.collapse_at:
                    print(f"조기 종료: 손실이 {args.collapse_at} 아래로 붕괴했다. "
                          f"쌍 {len(pairs)}개에 과적합한 것이다.", flush=True)
                    collapsed = True
                    break
        print(f"에폭 {epoch + 1} 평균 손실 {sum(losses) / len(losses):.5f}", flush=True)
        if collapsed:
            break

    args.out.mkdir(parents=True, exist_ok=True)
    adapter_weights = dict(_tf(model.trainable_parameters()))
    mx.save_safetensors(str(args.out / "adapters.safetensors"), adapter_weights)
    config = json.loads((args.base_adapter / "adapter_config.json").read_text(encoding="utf-8"))
    (args.out / "adapter_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"\n저장: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
