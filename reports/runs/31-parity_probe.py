"""엔진 대조에서 갈린 시나리오를 개별로 연다.

**불일치 건수만 보고 통과시키지 않는다.** 리포트 22번과 23번이 정한 절차가 "1~5종은
첫 분기 지점의 로짓 간격을 확인해야 통과"다. 간격이 ULP 자리면 수치적으로 미결정된
자리이고, 크면 설정이 다른 것이다.

**두 번 틀리고 고친 기록을 남긴다.**

1. 토큰 **문자열**로 맞댔다. 한국어는 한 글자가 여러 토큰으로 쪼개지고 디코딩이 바이트
   경계에서 어긋나 없는 불일치가 생긴다
2. llama.cpp의 `completion_probabilities`를 토큰 배열로 썼다. **그 배열은 쪼개진
   멀티바이트 토큰을 하나 빼먹는다.** 실측으로 확인했다(tokens는 60985를 포함하는데
   확률 배열에는 없다). 그래서 첫 분기 위치가 한 칸 밀렸다

그래서 지금은 (1) 샘플된 토큰은 `tokens` 필드에서 읽고 (2) 간격은 **공통 접두사를 다시
먹여 그 자리에서 한 토큰만 뽑아** 잰다. 정렬을 추측하지 않는다.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.analyzer import PROMPT_VARIANTS, build_prompt
from harness.engines import LlamaCppEngine
from harness.loading import ScenarioLoader

GGUF = "training/gguf/sft-v6-s1-bf16.gguf"
MERGED = "training/merged/sft-v6-s1-bf16"
ULP = 0.125  # bf16, 로짓 크기 16~32 구간
NAMES = sys.argv[1:] or ["monitor-error-budget-burn-slow-11", "monitor-5xx-redis-connection-failure"]


def post(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as res:
        return json.loads(res.read().decode("utf-8"))


def main() -> int:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    system = PROMPT_VARIANTS["production"]
    loader = ScenarioLoader()
    tok = AutoTokenizer.from_pretrained(MERGED)
    model = AutoModelForCausalLM.from_pretrained(MERGED, dtype="auto").to("mps").eval()
    engine = LlamaCppEngine(GGUF, port=18085)

    try:
        for name in NAMES:
            scenario = loader.load_file(Path(f"golden-set/monitor/{name}.json"))
            print(f"\n## {name}")
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content": build_prompt(scenario)}]

            torch_prompt = tok.apply_chat_template(messages, tokenize=False,
                                                   add_generation_prompt=True)
            served = post(f"{engine.base_url}/apply-template", {"messages": messages})["prompt"]
            print(f"프롬프트 문자열 일치: {torch_prompt == served}")

            comp = post(f"{engine.base_url}/completion", {
                "prompt": served, "n_predict": 700, "temperature": 0.0, "top_k": 0,
                "top_p": 1.0, "min_p": 0.0, "repeat_penalty": 1.0, "seed": 20260826,
                "cache_prompt": False, "return_tokens": True})
            llama_ids = [int(t) for t in comp["tokens"]]

            enc = tok(torch_prompt, return_tensors="pt").to("mps")
            with torch.no_grad():
                out = model.generate(**enc, max_new_tokens=700, do_sample=False,
                                     temperature=None, top_p=None, repetition_penalty=1.0,
                                     pad_token_id=tok.pad_token_id or tok.eos_token_id,
                                     return_dict_in_generate=True, output_scores=True)
            torch_ids = [int(t) for t in out.sequences[0][enc["input_ids"].shape[1]:]]

            limit = min(len(torch_ids), len(llama_ids))
            first = next((i for i in range(limit) if torch_ids[i] != llama_ids[i]), None)
            if first is None:
                print(f"생성 토큰 {limit}개까지 전부 일치 "
                      f"(길이 torch {len(torch_ids)} / llama {len(llama_ids)})")
                continue

            print(f"첫 분기 {first}번째: torch id={torch_ids[first]} "
                  f"{tok.decode([torch_ids[first]])!r} / llama id={llama_ids[first]} "
                  f"{tok.decode([llama_ids[first]])!r}")

            scores = out.scores[first][0].float()
            top = scores.topk(2)
            gap_t = float(top.values[0] - top.values[1])
            print(f"  torch 상위 2개 id={int(top.indices[0])} id={int(top.indices[1])}"
                  f"  간격 {gap_t:.5f} (ULP {ULP}의 {gap_t / ULP:.1f}배)")

            # 같은 접두사를 다시 먹여 그 자리 한 토큰만 뽑는다. 프롬프트는 문자열로 주고
            # 접두사 토큰은 id로 이어붙여, 서버가 프롬프트를 어떻게 토큰화하든 접두사가 같다
            one = post(f"{engine.base_url}/completion", {
                "prompt": [served] + torch_ids[:first], "n_predict": 1, "temperature": 0.0,
                "top_k": 0, "top_p": 1.0, "min_p": 0.0, "repeat_penalty": 1.0,
                "n_probs": 5, "seed": 20260826, "cache_prompt": False})
            probs = (one.get("completion_probabilities") or [{}])[0].get("top_logprobs") or []
            if len(probs) >= 2:
                gap_l = float(probs[0]["logprob"] - probs[1]["logprob"])
                print(f"  llama 상위 2개 id={probs[0]['id']} id={probs[1]['id']}"
                      f"  간격 {gap_l:.5f} (ULP {ULP}의 {gap_l / ULP:.1f}배)")
                same_set = {int(probs[0]["id"]), int(probs[1]["id"])} == {
                    int(top.indices[0]), int(top.indices[1])}
                print(f"  상위 2개 집합 일치: {same_set}")
            else:
                print(f"  llama 원본: {json.dumps(probs, ensure_ascii=False)[:300]}")
    finally:
        engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
