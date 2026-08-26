"""로컬 모델의 출력 형식 준수율만 잰다. judge를 부르지 않으므로 API 비용이 없다.

소형 모델의 알려진 실패 모드가 구조화 출력이라, 데이터에 비용을 쓰기 전에 여기서 확인한다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness.analyzer import PROMPT_VARIANTS, build_prompt, parse_analysis
from harness.local_model import DEFAULT_MODEL, MlxJsonClient
from harness.loading import ScenarioLoader


def main() -> int:
    parser = argparse.ArgumentParser(description="로컬 모델 출력 형식 스모크")
    parser.add_argument("--model-path", default=DEFAULT_MODEL)
    parser.add_argument("--adapter-path", default=None)
    parser.add_argument("--scenarios-dir", type=Path, default=Path("golden-set/monitor"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--prompt-variant", default="production", choices=sorted(PROMPT_VARIANTS))
    args = parser.parse_args()

    scenarios = ScenarioLoader().load_dir(args.scenarios_dir)[: args.limit]
    client = MlxJsonClient(args.model_path, adapter_path=args.adapter_path)
    system = PROMPT_VARIANTS[args.prompt_variant]

    parsed, failures = 0, []
    for scenario in scenarios:
        raw = client.generate_json(system, build_prompt(scenario))
        try:
            analysis = parse_analysis(raw)
            parsed += 1
            print(f"[OK  ] {scenario.name} | 근거={analysis.evidence_found} "
                  f"요약={analysis.summary[:40]}")
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            failures.append((scenario.name, str(e), raw[:200]))
            print(f"[FAIL] {scenario.name} | {e}")

    total = len(scenarios)
    print(f"\n파싱 성공 {parsed}/{total} ({100.0 * parsed / total:.0f}%)")
    for name, err, raw in failures:
        print(f"- {name}: {err}\n  raw: {raw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
