"""PEFT 어댑터를 베이스 가중치에 병합해 HF 포맷으로 저장한다. GGUF 변환의 입력이다.

llama.cpp의 변환기는 LoRA가 얹힌 상태를 모른다. 가중치가 하나로 합쳐진 모델을 받아야 하므로
병합이 선행되어야 한다.

**병합은 조용히 틀릴 수 있다.** 스케일 규약(alpha/r)이 어긋나면 어댑터 효과가 몇 분의 일로
걸리는데 출력은 그럴듯하게 나온다(리포트 23번). 그래서 저장한 뒤 디스크에서 다시 읽어
병합 전(base + peft)과 첫 토큰 로짓을 맞댄다. 대조 없이 넘어가면 GGUF부터 그 아래가 전부
틀린 가중치 위에 선다.

    .venv312/bin/python -m training.merge_cli \
      --adapter training/adapters/sft-v6-s1-peft \
      --out training/merged/sft-v6-s1-bf16
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from harness.analyzer import PROMPT_VARIANTS, build_prompt
from harness.loading import ScenarioLoader


def _base_from_adapter(adapter: Path) -> str:
    config = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8"))
    base = config.get("base_model_name_or_path")
    if not base:
        raise ValueError(f"{adapter}/adapter_config.json에 base_model_name_or_path가 없다")
    return base


def _ulp(value: float) -> float:
    """bfloat16의 최소 표현 단위. 유효 8비트라 값의 지수에 따라 달라진다."""
    if value == 0:
        return 0.0
    return 2.0 ** (math.floor(math.log2(abs(value))) - 7)


def _last_logits(model, tok, system: str, prompt: str, device: str):
    import torch

    text = tok.apply_chat_template(
        [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        tokenize=False, add_generation_prompt=True)
    enc = tok(text, return_tensors="pt").to(device)
    with torch.no_grad():
        out = model(**enc)
    return out.logits[0, -1, :].float().cpu()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--base", default=None, help="기본값은 adapter_config.json에서 읽는다")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scenarios-dir", type=Path, default=Path("golden-set/monitor"))
    parser.add_argument("--prompt-variant", default="production", choices=sorted(PROMPT_VARIANTS))
    parser.add_argument("--verify", type=int, default=3, help="대조할 시나리오 수. 0이면 건너뛴다")
    parser.add_argument("--device", default="mps")
    args = parser.parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base_id = args.base or _base_from_adapter(args.adapter)
    print(f"[병합] base={base_id}")
    print(f"[병합] adapter={args.adapter}")

    tok = AutoTokenizer.from_pretrained(base_id)
    # 정밀도는 체크포인트에서 물려받는다. 하드코딩하면 bf16 모델이 fp16으로 내려가 출력이 무너진다(리포트 22번)
    model = AutoModelForCausalLM.from_pretrained(base_id, dtype="auto").to(args.device)
    model = PeftModel.from_pretrained(model, str(args.adapter))
    model.eval()
    print(f"[병합] dtype={next(model.parameters()).dtype}")

    system = PROMPT_VARIANTS[args.prompt_variant]
    scenarios = []
    before = []
    if args.verify:
        scenarios = ScenarioLoader().load_dir(args.scenarios_dir)[: args.verify]
        before = [_last_logits(model, tok, system, build_prompt(s), args.device) for s in scenarios]
        print(f"[검증] 병합 전 로짓 확보 {len(before)}종")

    merged = model.merge_and_unload()
    merged.eval()
    args.out.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(args.out))
    tok.save_pretrained(str(args.out))
    print(f"[병합] 저장 완료 {args.out}")

    if not args.verify:
        return 0

    del model, merged
    if args.device == "mps":
        torch.mps.empty_cache()

    reloaded = AutoModelForCausalLM.from_pretrained(str(args.out), dtype="auto").to(args.device)
    reloaded.eval()
    print(f"[검증] 재적재 dtype={next(reloaded.parameters()).dtype}")

    failures = 0
    for scenario, ref in zip(scenarios, before):
        got = _last_logits(reloaded, tok, system, build_prompt(scenario), args.device)
        diff = (got - ref).abs()
        peak = max(abs(float(ref.max())), abs(float(ref.min())))
        ulp = _ulp(peak)
        max_diff = float(diff.max())
        same_argmax = int(ref.argmax()) == int(got.argmax())
        top5 = [int(i) for i in ref.topk(5).indices] == [int(i) for i in got.topk(5).indices]
        ok = same_argmax and top5
        failures += 0 if ok else 1
        print(f"  {scenario.name}")
        print(f"    최대차 {max_diff:.5f} (ULP {ulp:.5f}의 {max_diff / ulp:.1f}배)"
              f"  중앙 {float(diff.median()):.5f}  argmax {same_argmax}  top5 {top5}")

    if failures:
        print(f"[검증] 실패 {failures}종. 병합 스케일이나 저장 경로를 의심한다")
        return 1
    print("[검증] 통과. 병합 전후가 같은 것을 계산한다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
