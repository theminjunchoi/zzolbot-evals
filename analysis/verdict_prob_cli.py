import json, sys
from pathlib import Path
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
from harness.analyzer import PROMPT_VARIANTS, build_prompt
from harness.constrained import CitationConstraint
from harness.loading import ScenarioLoader
from analysis.verdict_prob import ProbeCapture, VerdictProbe

ARMS = {"base": None, "v4": "training/adapters/sft-v4-s1", "v6": "training/adapters/sft-v6-s1",
        "v7": "training/adapters/sft-v7-s1", "dpo": "training/adapters/dpo-v2-s1"}
OUT = Path("reports/runs/verdict-prob"); OUT.mkdir(parents=True, exist_ok=True)
sc = ScenarioLoader().load_dir(Path("golden-set/monitor"))
for name, ad in ARMS.items():
    path = OUT / f"{name}.json"
    if path.exists():
        print(f"[{name}] 이미 완료, 건너뜀", flush=True); continue
    m, tok = load("mlx-community/Qwen2.5-1.5B-Instruct-4bit", adapter_path=ad)
    pv = VerdictProbe.build(tok)
    probs = {}
    for i, s in enumerate(sc, 1):
        p = tok.apply_chat_template([{"role":"system","content":PROMPT_VARIANTS["production"]},
                                     {"role":"user","content":build_prompt(s)}],
                                    tokenize=False, add_generation_prompt=True)
        cap = ProbeCapture(pv)
        generate(m, tok, p, max_tokens=700, sampler=make_sampler(temp=0.0),
                 logits_processors=[cap, CitationConstraint(tok, list(s.log_samples))], verbose=False)
        probs[s.name] = cap.prob_true
        if i % 10 == 0: print(f"[{name}] {i}/33", flush=True)
    path.write_text(json.dumps(probs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{name}] 저장 완료", flush=True)
