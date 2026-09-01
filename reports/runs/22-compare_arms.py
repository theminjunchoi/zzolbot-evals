"""두 백엔드의 결과를 시나리오 단위로 맞댄다.

평균만 보면 안 된다. 베이스 모델은 점수가 낮은 구간이라 **서로 다른 방식으로 틀려도
평균은 비슷하게 나온다.** 판정은 시나리오별 불일치 건수로 한다.

보상 배점이 형식 0.1 + 판정 0.5 + 인용 0.4이므로 차이의 크기가 무엇이 갈렸는지를 말해준다.
"""
import json, sys
from pathlib import Path

a_path, b_path = Path(sys.argv[1]), Path(sys.argv[2])
a = json.loads(a_path.read_text())
b = json.loads(b_path.read_text())
arm = sys.argv[3] if len(sys.argv) > 3 else "base"
ga, gb = a[arm]["greedy"], b[arm]["greedy"]

assert set(ga) == set(gb), "시나리오 집합이 다르다"
names = sorted(ga)


def component(d: float) -> str:
    m = abs(d)
    if m < 1e-9:      return "-"
    if abs(m - 0.5) < 0.06:  return "판정"
    if abs(m - 0.4) < 0.06:  return "인용"
    if abs(m - 0.9) < 0.06:  return "판정+인용"
    if abs(m - 0.1) < 0.06:  return "형식"
    return f"기타({m:.2f})"


diffs = [(n, ga[n], gb[n]) for n in names if abs(ga[n] - gb[n]) > 1e-9]
print(f"# 백엔드 대조: {a_path.stem} 대 {b_path.stem}  (팔 {arm})\n")
print(f"시나리오 {len(names)}종")
print(f"평균 보상: {sum(ga.values())/len(ga):.4f} 대 {sum(gb.values())/len(gb):.4f}")
print(f"**불일치 {len(diffs)}종 / {len(names)}종**\n")
if diffs:
    print("| 시나리오 | A | B | 차이 | 갈린 항목 |")
    print("|---|---|---|---|---|")
    for n, x, y in sorted(diffs, key=lambda t: -abs(t[1]-t[2])):
        print(f"| {n} | {x:.2f} | {y:.2f} | {y-x:+.2f} | {component(y-x)} |")
else:
    print("불일치 없음. 33종 전부 같은 점수다.")
