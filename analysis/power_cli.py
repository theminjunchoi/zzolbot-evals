"""검정력과 필요 표본 계산 진입점.

    python -m analysis.power_cli --a gate-greedy:base --b gate-greedy:v4
    python -m analysis.power_cli --a gate-greedy:v4 --b gate-greedy:v3 --target 0.04
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analysis.power import alert_of, cluster_sizes, load_arm, paired_bootstrap


def parse_ref(raw: str) -> tuple[str, str]:
    label, _, arm = raw.partition(":")
    if not arm:
        raise argparse.ArgumentTypeError(f"형식은 라벨:팔 이다: {raw}")
    return label, arm


def main() -> int:
    p = argparse.ArgumentParser(description="짝지은 부트스트랩 검정력 계산")
    p.add_argument("--a", required=True, type=parse_ref, help="기준 팔 (라벨:팔)")
    p.add_argument("--b", required=True, type=parse_ref, help="비교 팔 (라벨:팔)")
    p.add_argument("--runs-dir", type=Path, default=Path("reports/runs"))
    p.add_argument("--scenarios-dir", type=Path, default=Path("golden-set/monitor"))
    p.add_argument("--target", type=float, default=0.0,
                   help="이 크기의 효과를 잡는 데 필요한 표본 수를 계산")
    p.add_argument("--iters", type=int, default=10000)
    p.add_argument("--by-scenario", action="store_true",
                   help="시나리오 단위로 재추출. 기본은 알림 단위(군집)다")
    a = p.parse_args()

    (la, aa), (lb, ab) = a.a, a.b
    arm_a = load_arm(a.runs_dir / f"{la}-reward.json", aa)
    arm_b = load_arm(a.runs_dir / f"{lb}-reward.json", ab)
    clusters = None if a.by_scenario else alert_of(a.scenarios_dir)
    r = paired_bootstrap(arm_a, arm_b, clusters, iters=a.iters)

    print(f"{la}:{aa}  ->  {lb}:{ab}")
    print(f"  재추출 단위 {r.unit}, 시나리오 {r.n}종, 군집 {r.n_clusters}개")
    print(f"  관측 차이 {r.observed:+.4f}   95% 구간 [{r.ci[0]:+.4f}, {r.ci[1]:+.4f}]")
    print(f"  표준오차 {r.se:.4f}")
    print(f"  MDE(80% 검정력) {r.mde:.4f}  ->  "
          f"{'유의' if abs(r.observed) > r.mde else '검출 불가'}")
    if a.target:
        print(f"  효과 {a.target:.4f}를 잡으려면 {r.n_for(a.target)}"
              f"{'개 알림' if r.unit == '알림' else '종'} 필요")
    if clusters:
        top = cluster_sizes(clusters, sorted(set(arm_a) & set(arm_b)))[:3]
        print(f"  군집 상위: " + ", ".join(f"{k}={v}" for k, v in top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
