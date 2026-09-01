"""왜 느려졌는가를 가르는 진단. 30스텝, 길이 고정, 스텝마다 전부 기록.

첫 게이트의 결함: 20스텝마다만 찍어서 step 3(2.4s)와 step 20(46.9s) 사이에 무슨 일이
있었는지 알 수 없었다. 길이도 샘플마다 달라(1489~2552) 시간 차이에 길이가 섞였다.

이번엔 둘을 고정하고 스텝마다 시간과 MPS 메모리를 같이 남긴다.
- 시간이 메모리와 함께 단조 증가 → 우리 문제(할당자가 안 놓아줌)
- 시간이 메모리와 무관하게 널뛰기 → 바깥 문제(GPU 경합)
"""
import json, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

MODEL, DATA, FIXED_LEN, STEPS = "Qwen/Qwen2.5-1.5B-Instruct", "training/data/sft-v6/train.jsonl", 1726, 30

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16).to("mps")
model.config.use_cache = False
n = model.config.num_hidden_layers
targets = [f"model.layers.{i}.self_attn.{p}" for i in range(n-16, n) for p in ("q_proj","v_proj")]
model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0,
                                         target_modules=targets, task_type="CAUSAL_LM"))
rows = [json.loads(l) for l in open(DATA)]
seqs = []
for r in rows:
    ids = tok(tok.apply_chat_template(r["messages"], tokenize=False), add_special_tokens=False)["input_ids"]
    if len(ids) >= FIXED_LEN:
        seqs.append(ids[:FIXED_LEN])          # 길이를 하나로 고정한다
print(f"길이 {FIXED_LEN} 고정, 사용 가능 샘플 {len(seqs)}개", flush=True)

opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
model.train()
print("step   sec   mps_alloc_GB", flush=True)
for step in range(STEPS):
    ids = torch.tensor([seqs[step % len(seqs)]], device="mps")
    torch.mps.synchronize(); t0 = time.time()
    out = model(input_ids=ids, labels=ids); out.loss.backward()
    opt.step(); opt.zero_grad(set_to_none=True)
    torch.mps.synchronize()
    print(f"{step+1:4d} {time.time()-t0:6.2f} {torch.mps.driver_allocated_memory()/2**30:8.2f}", flush=True)
