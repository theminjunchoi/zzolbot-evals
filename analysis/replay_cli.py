"""운영 로그 재생 측정.

골든셋이 아니라 **실제 운영 Loki 로그**로 만든 시나리오에 두 모델을 나란히 통과시킨다.
알림이 거의 발화하지 않아(30일에 1종류) 섀도우 기록만으로는 표본이 모이지 않는다.
로그는 매일 쌓이므로 그쪽에서 입력을 가져온다.

**무엇을 재고 무엇을 못 재나.**

- 음성 케이스는 구성으로 라벨이 있다. 알림을 무관한 계열로 짝지었으므로 정답이 "근거 없음"이다.
  여기서는 **오탐률**을 잰다.
- 양성 케이스는 라벨이 없다. 알림이 로그와 맞더라도 양적 정합성(표본 2건으로 급증을 설명할 수
  있는가) 때문에 정답이 갈린다. 여기서는 **두 모델의 일치율과 인용 접지율**만 본다.
  정답률을 잰다고 말하지 않는다.

프롬프트 조립, JSON 추출, 접지는 두 팔이 한 벌을 공유한다. 갈라지면 차이의 원인을 모델로
좁힐 수 없다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from harness.analyzer import PROMPT_VARIANTS, build_prompt, parse_analysis
from harness.domain import Scenario
from harness.grounding import GroundingPipeline
from harness.replay import build_windows, load_lines, to_scenarios

DEFAULT_GGUF = "training/gguf/sft-v6-s1-q8_0.gguf"


@dataclass
class Outcome:
    name: str
    is_negative: bool
    parse_ok: bool
    claimed: bool
    grounded: bool
    raw: str


def _settle(scenario: Scenario, raw: str, grounding: GroundingPipeline) -> Outcome:
    is_negative = scenario.expected == "아니오"
    try:
        analysis = parse_analysis(raw)
    except Exception:
        return Outcome(scenario.name, is_negative, False, False, False, raw)
    settled = grounding.apply(analysis, scenario)
    return Outcome(scenario.name, is_negative, True, analysis.evidence_found, settled.grounded, raw)


def run_gemini(scenarios: list[Scenario], model: str, variant: str, min_interval: float) -> list[Outcome]:
    from harness.llm import GeminiJsonClient

    client = GeminiJsonClient(api_key=os.environ["GEMINI_ZZOL_BOT_API_KEY"], model=model,
                              min_interval_s=min_interval)
    grounding = GroundingPipeline()
    system = PROMPT_VARIANTS[variant]
    out = []
    for i, s in enumerate(scenarios, 1):
        raw = client.generate_json(system, build_prompt(s))
        out.append(_settle(s, raw, grounding))
        print(f"  [gemini] {i}/{len(scenarios)} {s.name} 주장={out[-1].claimed} 접지={out[-1].grounded}",
              flush=True)
    return out


def run_local(scenarios: list[Scenario], gguf: str, variant: str, max_tokens: int) -> list[Outcome]:
    from harness.engines import make_engine

    engine = make_engine("llamacpp", gguf, None)
    print(f"  [local] 엔진 llamacpp, 정밀도 {engine.dtype}", flush=True)
    grounding = GroundingPipeline()
    system = PROMPT_VARIANTS[variant]
    out = []
    try:
        for i, s in enumerate(scenarios, 1):
            # 운영과 같은 제약 디코딩. log_samples 를 주면 인용을 문법으로 묶는다.
            raw = engine.generate(system, build_prompt(s), log_samples=list(s.log_samples),
                                  temp=0.0, max_tokens=max_tokens)[0]
            out.append(_settle(s, raw, grounding))
            print(f"  [local] {i}/{len(scenarios)} {s.name} 주장={out[-1].claimed} 접지={out[-1].grounded}",
                  flush=True)
    finally:
        closer = getattr(engine, "close", None)
        if closer is not None:
            closer()
    return out


def summarize(gem: list[Outcome], loc: list[Outcome]) -> str:
    by_name = {o.name: o for o in loc}
    lines = []

    def block(title: str, pick) -> None:
        g = [o for o in gem if pick(o)]
        l = [by_name[o.name] for o in g if o.name in by_name]
        if not g:
            return
        lines.append(f"\n### {title} ({len(g)}종)\n")
        lines.append("| 지표 | Gemini | 자체 모델 |")
        lines.append("|---|---|---|")
        lines.append(f"| 형식 실패 | {sum(1 for o in g if not o.parse_ok)} | {sum(1 for o in l if not o.parse_ok)} |")
        lines.append(f"| 근거 주장(접지 전) | {sum(1 for o in g if o.claimed)} | {sum(1 for o in l if o.claimed)} |")
        lines.append(f"| 접지 통과 | {sum(1 for o in g if o.grounded)} | {sum(1 for o in l if o.grounded)} |")

    block("음성 (알림과 무관한 로그 · 정답은 근거 없음)", lambda o: o.is_negative)
    block("양성 (알림과 맞는 로그 · 라벨 없음)", lambda o: not o.is_negative)

    agree = sum(1 for o in gem if o.name in by_name and o.grounded == by_name[o.name].grounded)
    total = sum(1 for o in gem if o.name in by_name)
    lines.append(f"\n### 두 모델 일치\n")
    lines.append(f"접지 후 판정 일치 {agree}/{total} ({100 * agree / total:.0f}%)\n")
    diff = [o.name for o in gem if o.name in by_name and o.grounded != by_name[o.name].grounded]
    if diff:
        lines.append("불일치 시나리오(손 검토 대상):\n")
        lines.append("```text")
        lines.extend(diff)
        lines.append("```")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="운영 로그 재생 측정")
    p.add_argument("--label", required=True)
    p.add_argument("--logs", type=Path, default=Path("raw/scratch-prod-replay/prod-errors.jsonl"))
    p.add_argument("--out-dir", type=Path, default=Path("reports/runs"))
    p.add_argument("--gguf", default=DEFAULT_GGUF)
    p.add_argument("--gemini", default="gemini-2.5-flash")
    p.add_argument("--prompt-variant", default="production", choices=sorted(PROMPT_VARIANTS))
    p.add_argument("--max-tokens", type=int, default=1400, help="운영 설정과 같게 둔다")
    p.add_argument("--min-interval", type=float, default=1.2)
    p.add_argument("--limit", type=int, default=0, help="앞에서 N종만. 연습 실행용")
    p.add_argument("--arms", default="gemini,local")
    args = p.parse_args()

    scenarios = to_scenarios(build_windows(load_lines(args.logs)))
    if args.limit:
        scenarios = scenarios[: args.limit]
    neg = sum(1 for s in scenarios if s.expected == "아니오")
    print(f"시나리오 {len(scenarios)}종 (양성 {len(scenarios) - neg}, 음성 {neg})", flush=True)

    arms = args.arms.split(",")
    gem = run_gemini(scenarios, args.gemini, args.prompt_variant, args.min_interval) if "gemini" in arms else []
    loc = run_local(scenarios, args.gguf, args.prompt_variant, args.max_tokens) if "local" in arms else []

    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.out_dir / f"{args.label}-raw.jsonl"
    with open(raw_path, "w", encoding="utf-8") as f:
        for arm, rows in (("gemini", gem), ("local", loc)):
            for o in rows:
                f.write(json.dumps({"arm": arm, "scenario": o.name, "negative": o.is_negative,
                                    "parse_ok": o.parse_ok, "claimed": o.claimed,
                                    "grounded": o.grounded, "raw": o.raw}, ensure_ascii=False) + "\n")

    report = f"# 재생 측정 {args.label}\n\n시나리오 {len(scenarios)}종 (양성 {len(scenarios) - neg}, 음성 {neg})\n"
    if gem and loc:
        report += summarize(gem, loc)
    print(report)
    (args.out_dir / f"{args.label}.md").write_text(report, encoding="utf-8")
    print(f"\n원본 {raw_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
