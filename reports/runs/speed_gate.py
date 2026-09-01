"""1번 속도 게이트. torch-fp16 MPS로 100스텝만 돌려 초당 스텝을 잰다.

MLX 기준선: sft-v6 781스텝을 약 50분 = 3.84 s/step (4bit, num-layers 16).
판정: 4배 이상 느리면(15.4 s/step 초과, 781스텝 환산 2시간 초과) 학습 경로를 갈아탄다.
"""
import json, time, sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DATA = "training/data/sft-v6/train.jsonl"
MAX_LEN = 3200
STEPS = 100

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16).to("mps")
model.config.use_cache = False

n_layers = model.config.num_hidden_layers
target_layers = set(range(n_layers - 16, n_layers))   # mlx-lm --num-layers 16 = 뒤에서 16개
targets = [f"model.layers.{i}.self_attn.{p}" for i in sorted(target_layers) for p in ("q_proj", "v_proj")]
model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0,
                                         target_modules=targets, task_type="CAUSAL_LM"))
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"layers={n_layers} lora_targets={len(targets)} trainable={trainable/1e6:.2f}M", flush=True)

rows = [json.loads(l) for l in open(DATA)]
seqs = []
for r in rows:
    text = tok.apply_chat_template(r["messages"], tokenize=False)
    ids = tok(text, add_special_tokens=False)["input_ids"]
    seqs.append(ids[:MAX_LEN])
lens = sorted(len(s) for s in seqs)
print(f"n={len(seqs)} len p50={lens[len(lens)//2]} p95={lens[int(len(lens)*0.95)]} max={lens[-1]}", flush=True)

opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
model.train()

times = []
for step in range(STEPS):
    ids = torch.tensor([seqs[step % len(seqs)]], device="mps")
    torch.mps.synchronize(); t0 = time.time()
    out = model(input_ids=ids, labels=ids)
    out.loss.backward()
    opt.step(); opt.zero_grad(set_to_none=True)
    torch.mps.synchronize()
    dt = time.time() - t0
    times.append(dt)
    if step < 3 or (step + 1) % 20 == 0:
        print(f"  step {step+1:3d}  {dt:5.2f}s  loss {out.loss.item():.4f}  len {ids.shape[1]}", flush=True)

warm = times[10:]                       # 앞 10스텝은 커널 컴파일이 섞여 버린다
warm_sorted = sorted(warm)
med = warm_sorted[len(warm_sorted)//2]
mean = sum(warm)/len(warm)
print()
print(f"=== 결과 (워밍업 10스텝 제외, n={len(warm)}) ===")
print(f"중앙값 {med:.2f} s/step   평균 {mean:.2f} s/step")
print(f"781스텝 환산: {med*781/60:.1f}분 (중앙값 기준)")
print(f"MLX 기준선 3.84 s/step 대비 {med/3.84:.2f}배")
print(f"메모리 최대 {torch.mps.driver_allocated_memory()/2**30:.1f} GB")
verdict = "통과" if med <= 15.36 else "탈락"
print(f"게이트(15.36 s/step 이하): {verdict}")
