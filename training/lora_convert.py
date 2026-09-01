"""MLX LoRA 어댑터를 peft 형식으로 바꾼다.

**왜 필요한가.** 두 엔진을 맞대려면 같은 어댑터를 양쪽에 얹을 수 있어야 한다. 각자
학습한 어댑터끼리 비교하면 차이가 학습에서 왔는지 추론에서 왔는지 못 가른다.

**모양과 스케일 규약이 다르다.** 실측한 값이다(training/adapters/sft-v6-s1).

    mlx   lora_a [in, r]   lora_b [r, out]   delta = scale * lora_b.T @ lora_a.T
    peft  lora_A [r, in]   lora_B [out, r]   delta = (alpha/r) * lora_B @ lora_A

따라서 `lora_A = lora_a.T`, `lora_B = lora_b.T`이고, mlx의 scale을 peft에서 내려면
`alpha = scale * r`이다. mlx 기본 scale이 20.0이고 rank가 8이므로 alpha는 160이다.
**alpha를 16으로 두면 스케일이 10분의 1이 되어 어댑터가 거의 안 걸린 것처럼 보인다.**
"""

from __future__ import annotations

import json
import re
from pathlib import Path

MLX_KEY = re.compile(r"^(?P<mod>model\.layers\.\d+\.[\w.]+)\.lora_(?P<ab>[ab])$")


def peft_key(mlx_key: str) -> str:
    """mlx 키를 peft 키로. peft는 base_model.model 접두와 .weight 접미를 붙인다."""
    m = MLX_KEY.match(mlx_key)
    if not m:
        raise ValueError(f"모르는 키 형식: {mlx_key}")
    return f"base_model.model.{m['mod']}.lora_{m['ab'].upper()}.weight"


def target_modules(mlx_keys) -> list[str]:
    """peft가 요구하는 대상 모듈 이름 목록. 레이어 번호를 뗀 접미 이름이다."""
    names = set()
    for k in mlx_keys:
        m = MLX_KEY.match(k)
        if m:
            names.add(m["mod"].split(".", 3)[3])   # model.layers.N. 이후
    return sorted(names)


def layers_of(mlx_keys) -> list[int]:
    return sorted({int(m.group(1)) for k in mlx_keys
                   if (m := re.match(r"^model\.layers\.(\d+)\.", k))})


def convert(src: Path, dst: Path, base_model: str) -> dict:
    """src(mlx 어댑터 디렉터리)를 dst(peft 어댑터 디렉터리)로 변환한다."""
    import numpy as np
    from safetensors.numpy import load_file, save_file

    cfg = json.loads((src / "adapter_config.json").read_text())
    lp = cfg["lora_parameters"]
    rank, scale = lp["rank"], lp["scale"]

    tensors = load_file(src / "adapters.safetensors")
    out = {}
    for k, v in tensors.items():
        # 전치가 핵심이다. 안 하면 모양이 맞아 보이는 경우가 있어 조용히 틀린다
        out[peft_key(k)] = np.ascontiguousarray(v.T)

    dst.mkdir(parents=True, exist_ok=True)
    save_file(out, str(dst / "adapter_model.safetensors"))
    peft_cfg = {
        "peft_type": "LORA", "task_type": "CAUSAL_LM",
        "base_model_name_or_path": base_model,
        "r": rank,
        "lora_alpha": scale * rank,          # peft 스케일 = alpha/r 이므로
        "lora_dropout": lp.get("dropout", 0.0),
        "target_modules": target_modules(tensors),
        "layers_to_transform": layers_of(tensors),
        "bias": "none", "fan_in_fan_out": False, "inference_mode": True,
        "init_lora_weights": True, "modules_to_save": None,
    }
    (dst / "adapter_config.json").write_text(json.dumps(peft_cfg, indent=2))
    return peft_cfg
