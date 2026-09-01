"""어텐션 구현과 그래디언트 체크포인팅이 메모리와 속도에 무엇을 하는가.

len 1726에서 MPS 메모리 14.1GB가 나왔다. 1.5B + LoRA 0.62M이 쓸 양이 아니다.
가장 긴 샘플(3086)로 네 조합을 재서 어느 설정이 학습 가능한지 정한다.
"""
import json, time, sys, gc
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

MODEL, DATA, LEN, STEPS = "Qwen/Qwen2.5-1.5B-Instruct", "training/data/sft-v6/train.jsonl", 3086, 6

tok = AutoTokenizer.from_pretrained(MODEL)
rows = [json.loads(l) for l in open(DATA)]
pool = []
for r in rows:
    ids = tok(tok.apply_chat_template(r["messages"], tokenize=False), add_special_tokens=False)["input_ids"]
    pool.append(ids)
pool.sort(key=len, reverse=True)
seq = (pool[0] + pool[1])[:LEN]          # 가장 긴 것 기준. 모자라면 이어붙여 길이를 맞춘다
print(f"측정 길이 {len(seq)}\n", flush=True)
print(f"{'attn':8} {'ckpt':6} {'peak_GB':>9} {'s/step':>8}", flush=True)

for attn in ("eager", "sdpa"):
    for ckpt in (False, True):
        torch.mps.empty_cache(); gc.collect()
        try:
            m = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16,
                                                     attn_implementation=attn).to("mps")
            m.config.use_cache = False
            n = m.config.num_hidden_layers
            tg = [f"model.layers.{i}.self_attn.{p}" for i in range(n-16, n) for p in ("q_proj","v_proj")]
            m = get_peft_model(m, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0,
                                             target_modules=tg, task_type="CAUSAL_LM"))
            if ckpt:
                m.gradient_checkpointing_enable()
                m.enable_input_require_grads()
            opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=1e-4)
            m.train()
            ids = torch.tensor([seq], device="mps")
            ts = []
            for s in range(STEPS):
                torch.mps.synchronize(); t0 = time.time()
                out = m(input_ids=ids, labels=ids); out.loss.backward()
                opt.step(); opt.zero_grad(set_to_none=True)
                torch.mps.synchronize(); ts.append(time.time()-t0)
            warm = sorted(ts[2:]); med = warm[len(warm)//2]
            peak = torch.mps.driver_allocated_memory()/2**30
            print(f"{attn:8} {str(ckpt):6} {peak:9.2f} {med:8.2f}", flush=True)
        except Exception as e:
            print(f"{attn:8} {str(ckpt):6} {'실패':>9} {str(e)[:50]}", flush=True)
        finally:
            del m, opt
            torch.mps.empty_cache(); gc.collect()
