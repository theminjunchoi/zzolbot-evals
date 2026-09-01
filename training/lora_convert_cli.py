"""mlx 어댑터를 peft 형식으로 변환하는 진입점.

    python -m training.lora_convert_cli training/adapters/sft-v6-s1 \
        --out training/adapters/sft-v6-s1-peft --base Qwen/Qwen2.5-1.5B-Instruct
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from training.lora_convert import convert


def main() -> int:
    p = argparse.ArgumentParser(description="mlx LoRA 어댑터를 peft 형식으로 변환")
    p.add_argument("src", type=Path, help="mlx 어댑터 디렉터리")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--base", required=True, help="베이스 모델 이름")
    a = p.parse_args()

    cfg = convert(a.src, a.out, a.base)
    print(f"{a.src} -> {a.out}")
    print(f"  r={cfg['r']} alpha={cfg['lora_alpha']} (스케일 {cfg['lora_alpha']/cfg['r']:.1f})")
    print(f"  모듈 {len(cfg['target_modules'])}종, 레이어 "
          f"{cfg['layers_to_transform'][0]}~{cfg['layers_to_transform'][-1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
