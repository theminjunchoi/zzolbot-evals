"""mlx 어댑터를 peft로 옮기는 규약을 고정한다.

**스케일이 가장 위험하다.** mlx는 scale을 그대로 곱하고 peft는 alpha/r을 곱한다.
alpha에 scale을 그대로 넣으면 어댑터 효과가 r분의 1이 되는데, 출력이 그럴듯하게
나오므로 조용히 틀린다.
"""

from __future__ import annotations

import json
import pytest

from training.lora_convert import convert, layers_of, peft_key, target_modules

np = pytest.importorskip("numpy")


def test_키를_peft_규약으로_바꾼다():
    got = peft_key("model.layers.12.self_attn.q_proj.lora_a")
    assert got == "base_model.model.model.layers.12.self_attn.q_proj.lora_A.weight"


def test_대상_모듈은_레이어_번호를_뗀_이름이다():
    keys = ["model.layers.12.self_attn.q_proj.lora_a",
            "model.layers.27.mlp.down_proj.lora_b"]
    assert target_modules(keys) == ["mlp.down_proj", "self_attn.q_proj"]
    assert layers_of(keys) == [12, 27]


def test_전치와_스케일_환산(tmp_path):
    from safetensors.numpy import load_file, save_file

    src, dst = tmp_path / "mlx", tmp_path / "peft"
    src.mkdir()
    a = np.random.randn(1536, 8).astype(np.float32)    # mlx lora_a [in, r]
    b = np.random.randn(8, 1536).astype(np.float32)    # mlx lora_b [r, out]
    save_file({"model.layers.12.self_attn.q_proj.lora_a": a,
               "model.layers.12.self_attn.q_proj.lora_b": b},
              str(src / "adapters.safetensors"))
    (src / "adapter_config.json").write_text(json.dumps(
        {"lora_parameters": {"rank": 8, "dropout": 0.0, "scale": 20.0}}))

    cfg = convert(src, dst, "some/model")
    out = load_file(str(dst / "adapter_model.safetensors"))
    A = out["base_model.model.model.layers.12.self_attn.q_proj.lora_A.weight"]
    B = out["base_model.model.model.layers.12.self_attn.q_proj.lora_B.weight"]
    assert A.shape == (8, 1536) and B.shape == (1536, 8)
    assert np.allclose(A, a.T) and np.allclose(B, b.T)

    # 같은 델타가 나와야 한다
    mlx_delta = 20.0 * (b.T @ a.T)
    peft_delta = (cfg["lora_alpha"] / cfg["r"]) * (B @ A)
    assert np.allclose(mlx_delta, peft_delta, atol=1e-4)
    assert cfg["lora_alpha"] == 160.0     # scale 20 * rank 8
