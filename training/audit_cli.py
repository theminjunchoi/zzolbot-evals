"""학습 데이터 전수 감사.

배치가 나뉘어 적재되면 각 실행 안에서만 중복이 걸러진다. 모든 배치가 끝난 뒤 한 번에
전수로 확인한다. 세 가지를 본다.

- 학습 후보끼리 내용 중복 (같은 문제를 여러 번 학습하면 그 패턴에 과적합한다)
- 평가 골든셋과의 겹침 (겹치면 평가 자체가 무의미해진다)
- 빌드된 train/valid 사이 누수 (같은 문제가 갈리면 valid 손실이 학습 진척을 재지 못한다)

사용 예:
    python -m training.audit_cli --candidate-dirs candidates/train-pilot candidates/train-main \\
        --data-dir training/data/train-v1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness.loading import ScenarioLoader
from harness.similarity import find_duplicates, normalize_message, signature


def user_signature(user_prompt: str) -> tuple:
    """빌드된 학습 파일에는 시나리오가 아니라 프롬프트 문자열만 있다.
    시나리오 시그니처와 같은 뼈대(알림 + 로그)를 프롬프트에서 복원해 비교한다.

    로그만 보면 **대조 쌍이 전부 중복으로 잡힌다.** 쌍은 로그를 고정하고 알림만 바꾼
    것이므로 로그가 같은 것이 정상이다. 알림을 넣지 않으면 정상 데이터를 문제로 신고한다.
    """
    lines = [l[2:] for l in user_prompt.splitlines() if l.startswith("- [")]
    alert = tuple(l for l in user_prompt.splitlines()
                  if l.startswith(("알림명:", "요약:", "설명(")))
    return (alert, tuple(normalize_message(l) for l in lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="학습 데이터 중복 전수 감사")
    parser.add_argument("--candidate-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--golden-dir", type=Path, default=Path("golden-set/monitor"))
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="빌드된 train.jsonl과 valid.jsonl이 있는 디렉터리")
    args = parser.parse_args()

    loader = ScenarioLoader()
    golden = loader.load_dir(args.golden_dir)
    candidates, seen = [], set()
    for directory in args.candidate_dirs:
        if not directory.exists():
            print(f"경고: 없는 디렉터리 {directory}", file=sys.stderr)
            continue
        for scenario in loader.load_dir(directory):
            if scenario.name in seen:
                print(f"[이름 중복] {scenario.name} (여러 배치에 존재)")
                continue
            seen.add(scenario.name)
            candidates.append(scenario)

    print(f"학습 후보 {len(candidates)}건, 골든셋 {len(golden)}종\n")
    problems = 0

    internal = find_duplicates(candidates)
    print(f"[1] 학습 후보끼리 내용 중복: {len(internal)}건")
    for later, earlier in internal:
        print(f"    {later}  ==  {earlier}")
    problems += len(internal)

    against_golden = find_duplicates(candidates, against=golden)
    print(f"[2] 평가 골든셋과 겹침: {len(against_golden)}건")
    for candidate, gold in against_golden:
        print(f"    {candidate}  ==  {gold}  (평가 오염)")
    problems += len(against_golden)

    if args.data_dir:
        rows = {}
        for split in ("train", "valid"):
            path = args.data_dir / f"{split}.jsonl"
            if not path.exists():
                continue
            rows[split] = [json.loads(line) for line in path.open(encoding="utf-8")]
        train_sigs = {user_signature(r["messages"][1]["content"]) for r in rows.get("train", [])}
        leaks = [r for r in rows.get("valid", [])
                 if user_signature(r["messages"][1]["content"]) in train_sigs]
        print(f"[3] train/valid 누수: {len(leaks)}건")
        for row in leaks:
            print(f"    valid 항목이 train에도 있음: {row['messages'][1]['content'][:60]}...")
        problems += len(leaks)

        golden_sigs = {tuple(normalize_message(l) for l in s.log_samples) for s in golden}
        contaminated = [r for split in rows.values() for r in split
                        if user_signature(r["messages"][1]["content"]) in golden_sigs]
        print(f"[4] 빌드된 학습 데이터와 골든셋 겹침: {len(contaminated)}건")
        problems += len(contaminated)

    print(f"\n총 문제 {problems}건")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
