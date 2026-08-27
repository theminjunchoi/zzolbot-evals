"""RFT 샘플링. 학습 프롬프트마다 여러 후보를 뽑아 보상으로 채점해 남긴다.

끊어서 실행할 수 있게 청크 단위로 저장한다. 노트북에서 한 시간 넘게 연속으로 돌리지
않으려는 목적이고, 중단해도 이미 끝난 청크는 다시 뽑지 않는다.

샘플별 점수를 **전부** 남긴다. 최고값만 남기면 "몇 번 중 몇 번 맞았나"를 알 수 없고,
그러면 잠재 능력과 우연을 구별하지 못한다(A단계에서 실제로 겪었다). 이 파일은 이어서
DPO의 선호 쌍 구성에도 그대로 쓰인다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from analysis.reward import RewardFunction, RewardSpec
from harness.analyzer import PROMPT_VARIANTS, build_prompt, parse_analysis
from harness.domain import Scenario
from harness.loading import ScenarioLoader
from harness.local_model import extract_json

DEFAULT_MODEL = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"


def score_text(reward: RewardFunction, scenario: Scenario, text: str) -> dict:
    """샘플 하나를 채점한다. 항목별 획득까지 남겨야 나중에 라벨 의존 여부로 나눠 볼 수 있다."""
    try:
        analysis = parse_analysis(extract_json(text))
    except Exception:  # noqa: BLE001 - 파싱 실패도 결과의 일부다
        breakdown = reward.score(scenario, None)
        return {"text": text, "total": breakdown.clamped, "parts": breakdown.parts,
                "parse_failed": True}
    breakdown = reward.score(scenario, analysis)
    return {"text": text, "total": breakdown.clamped, "parts": breakdown.parts,
            "parse_failed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="RFT용 후보 샘플링")
    parser.add_argument("--adapter", default="", help="출발 정책의 어댑터. 비면 베이스")
    parser.add_argument("--scenarios-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--temp", type=float, default=0.8)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--chunk", type=int, default=50, help="이 개수마다 저장하고 끊는다")
    parser.add_argument("--limit", type=int, default=0, help="앞에서 N개만 (0=전체)")
    parser.add_argument("--local-model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-variant", default="production", choices=sorted(PROMPT_VARIANTS))
    args = parser.parse_args()

    from mlx_lm import batch_generate, generate, load
    from mlx_lm.sample_utils import make_sampler

    scenarios = ScenarioLoader().load_dir(args.scenarios_dir)
    if args.limit:
        scenarios = scenarios[:args.limit]

    args.out.mkdir(parents=True, exist_ok=True)
    done = {p.stem for p in args.out.glob("*.json")}
    todo = [s for s in scenarios if s.name not in done]
    print(f"시나리오 {len(scenarios)}종 중 {len(done)}종 완료, {len(todo)}종 남음", flush=True)
    if not todo:
        return 0

    model, tok = load(args.local_model, adapter_path=args.adapter or None)
    reward = RewardFunction(RewardSpec())
    system = PROMPT_VARIANTS[args.prompt_variant]
    greedy_sampler = make_sampler(temp=0.0)
    warm_sampler = make_sampler(temp=args.temp, top_p=args.top_p)

    processed = 0
    for scenario in todo:
        text_prompt = tok.apply_chat_template(
            [{"role": "system", "content": system},
             {"role": "user", "content": build_prompt(scenario)}],
            tokenize=False, add_generation_prompt=True)

        greedy_text = generate(model, tok, text_prompt, max_tokens=700,
                               sampler=greedy_sampler, verbose=False)
        greedy = score_text(reward, scenario, greedy_text)

        ids = [tok.encode(text_prompt)] * args.samples
        texts: list[str] = []
        for start in range(0, args.samples, args.batch):
            texts.extend(batch_generate(model, tok, ids[start:start + args.batch],
                                        max_tokens=700, sampler=warm_sampler,
                                        verbose=False).texts)
        samples = [score_text(reward, scenario, t) for t in texts]

        (args.out / f"{scenario.name}.json").write_text(
            json.dumps({"scenario": scenario.name, "greedy": greedy, "samples": samples},
                       ensure_ascii=False), encoding="utf-8")
        processed += 1
        best = max(s["total"] for s in samples)
        print(f"  {processed}/{len(todo)} {scenario.name} "
              f"그리디 {greedy['total']:.2f} 최고 {best:.2f} "
              f"만점 {sum(1 for s in samples if s['total'] >= 0.999)}/{args.samples}", flush=True)
        if args.chunk and processed % args.chunk == 0:
            print(f"청크 {args.chunk}건 완료. 같은 명령으로 이어서 실행하면 남은 것만 뽑는다.")
            return 0
    print(f"\n전체 완료: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
