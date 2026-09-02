"""크기별 (학습 후 - 학습 전) 차이를 사전 등록한 기준으로 판정한다.

기준(리포트 25번 5절, 결과 전 커밋):
  재현    차이가 MDE를 넘고 부호가 양수
  미재현  차이가 MDE 아래이거나 음수
  보류    파싱 실패가 33종 중 5종을 넘음 (종점이 형식 실패에 오염)
"""
import json
from pathlib import Path
from analysis.power import alert_of, load_arm, paired_bootstrap

R = Path("reports/runs")
clusters = alert_of(Path("golden-set/monitor"))

# (표시명, 학습 전 파일:팔, 학습 후 파일:팔)
ARMS = [
    ("0.5B", ("size-0p5b", "base"), ("size-0p5b", "trained")),
    ("1.5B", ("gate-greedy", "base"), ("v6", "v6")),          # 기존 측정 재사용
    ("3B",   ("size-3b", "base"),   ("size-3b", "trained")),
]

print(f"{'크기':6} {'학습 전':>8} {'학습 후':>8} {'차이':>9} {'SE':>7} {'MDE':>7} {'95% 구간':>20}  판정")
rows = []
for name, (fa, aa), (fb, ab) in ARMS:
    pa, pb = R / f"{fa}-reward.json", R / f"{fb}-reward.json"
    if not (pa.exists() and pb.exists()):
        print(f"{name:6}  (아직 없음: {pa.name if not pa.exists() else pb.name})")
        continue
    a, b = load_arm(pa, aa), load_arm(pb, ab)
    r = paired_bootstrap(a, b, clusters)
    mean_a = sum(a.values()) / len(a)
    mean_b = sum(b.values()) / len(b)
    verdict = "재현" if (r.observed > r.mde) else "미재현"
    print(f"{name:6} {mean_a:8.4f} {mean_b:8.4f} {r.observed:+9.4f} {r.se:7.4f} {r.mde:7.4f}"
          f"  [{r.ci[0]:+.4f}, {r.ci[1]:+.4f}]  {verdict}")
    rows.append((name, r))

if len(rows) >= 2:
    print()
    print("=== 크기 간 효과 차이 (상호작용). 리포트 24번대로 검출력이 없을 것 ===")
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            n1, r1 = rows[i]; n2, r2 = rows[j]
            print(f"  {n1} 효과 {r1.observed:+.4f} 대 {n2} 효과 {r2.observed:+.4f}"
                  f"   차이 {r2.observed - r1.observed:+.4f}"
                  f"  (개별 MDE {r1.mde:.3f}, {r2.mde:.3f})")
    print("  주의: 이 차이의 유의성은 별도 상호작용 부트스트랩이 필요하고,")
    print("        리포트 24번에서 약 337종이 필요하다고 계산했다. 참고값일 뿐이다.")
