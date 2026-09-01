"""짝지은 부트스트랩으로 검정력과 필요 표본을 계산한다.

**왜 도구로 만드는가.** 이 레포는 검정력 계산을 이미 두 번 임시로 했다(리포트 09번의
906종, 19번의 110종). 매번 다시 짜면 정의가 어긋난다. 반복 실패 2번이다.

**군집 부트스트랩이 기본이다.** 리포트 20번에서 시나리오 단위로 재추출하면 구간을
1.7배 좁게 보는 것이 드러났다. 같은 알림에서 나온 시나리오는 독립이 아니고, 무엇보다
군집 크기가 고르지 않다(`AppErrorLogSpike` 하나가 33종 중 7종). 알림 단위가 맞는
질문은 "새 알림 종류가 와도 되는가"이고 운영에서 만나는 것은 그쪽이다.

**주의: 이 도구는 짝지은 비교만 한다.** 두 팔이 **같은 시나리오 집합**에서 측정돼야
한다. 짝을 지으면 시나리오 난이도 분산이 상쇄돼 검정력이 크게 오른다.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# 80% 검정력, 양측 5%에서 필요한 효과 크기 배수. z(0.975) + z(0.8) = 1.96 + 0.84
MDE_MULTIPLIER = 2.80


@dataclass(frozen=True)
class PairedResult:
    n: int
    n_clusters: int
    observed: float
    se: float
    ci: tuple[float, float]
    unit: str

    @property
    def mde(self) -> float:
        """80% 검정력으로 잡을 수 있는 최소 효과."""
        return MDE_MULTIPLIER * self.se

    def n_for(self, effect: float) -> int:
        """주어진 효과를 80% 검정력으로 잡는 데 필요한 표본 수.

        표준오차가 sqrt(n)에 반비례한다고 보고 환산한다. 군집 단위면 군집 수다.
        """
        if effect <= 0:
            raise ValueError("효과는 양수여야 한다")
        base = self.n_clusters if self.unit == "알림" else self.n
        return int(np.ceil(base * (self.mde / effect) ** 2))


def load_arm(path: Path, arm: str) -> dict[str, float]:
    return json.loads(path.read_text())[arm]["greedy"]


def paired_bootstrap(a: dict[str, float], b: dict[str, float],
                     clusters: dict[str, str] | None = None,
                     iters: int = 10000, seed: int = 20260901) -> PairedResult:
    """b - a의 짝지은 평균 차이를 부트스트랩한다.

    clusters가 주어지면 **시나리오가 아니라 군집을 재추출한다.** 군집을 통째로
    뽑고 빼는 것이 실제 표본 변동에 가깝다.
    """
    names = sorted(set(a) & set(b))
    if len(names) != len(a) or len(names) != len(b):
        raise ValueError(f"시나리오 집합이 다르다: {len(a)} 대 {len(b)}, 공통 {len(names)}")
    diff = np.array([b[n] - a[n] for n in names])
    rng = np.random.default_rng(seed)

    if clusters is None:
        unit, groups = "시나리오", [[i] for i in range(len(names))]
    else:
        unit = "알림"
        by: dict[str, list[int]] = {}
        for i, n in enumerate(names):
            by.setdefault(clusters[n], []).append(i)
        groups = list(by.values())

    k = len(groups)
    means = np.empty(iters)
    for t in range(iters):
        pick = rng.integers(0, k, k)
        idx = np.concatenate([groups[j] for j in pick])
        means[t] = diff[idx].mean()

    lo, hi = np.percentile(means, [2.5, 97.5])
    return PairedResult(n=len(names), n_clusters=k, observed=float(diff.mean()),
                        se=float(means.std(ddof=1)), ci=(float(lo), float(hi)), unit=unit)


def alert_of(scenarios_dir: Path) -> dict[str, str]:
    """시나리오 이름 -> 알림 이름. 군집 부트스트랩의 군집 정의다."""
    out = {}
    for f in sorted(scenarios_dir.glob("*.json")):
        d = json.loads(f.read_text())
        if "alert" in d and "name" in d:
            out[d["name"]] = d["alert"]["alertname"]
    return out


def cluster_sizes(clusters: dict[str, str], names) -> list[tuple[str, int]]:
    c: dict[str, int] = {}
    for n in names:
        c[clusters[n]] = c.get(clusters[n], 0) + 1
    return sorted(c.items(), key=lambda kv: -kv[1])
