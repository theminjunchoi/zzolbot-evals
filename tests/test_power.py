"""검정력 계산의 계약을 고정한다.

**짝을 지을 수 없으면 실패해야 한다.** 서로 다른 시나리오 집합을 비교하면 조용히
틀린 값이 나오는데, 이 레포는 같은 종류의 사고를 이미 여러 번 겪었다.
"""

from __future__ import annotations

import pytest

from analysis.power import MDE_MULTIPLIER, paired_bootstrap

np = pytest.importorskip("numpy")


def arm(vals):
    return {f"s{i}": v for i, v in enumerate(vals)}


def test_시나리오_집합이_다르면_거부한다():
    with pytest.raises(ValueError, match="시나리오 집합이 다르다"):
        paired_bootstrap({"a": 1.0}, {"b": 1.0})


def test_차이가_없으면_구간이_0을_포함한다():
    v = [0.2, 0.5, 0.9, 0.4, 0.7, 0.1]
    r = paired_bootstrap(arm(v), arm(v), iters=2000)
    assert r.observed == 0.0
    assert r.ci[0] <= 0.0 <= r.ci[1]
    assert r.se == pytest.approx(0.0, abs=1e-12)


def test_일정한_차이는_표준오차가_0이다():
    """모든 시나리오에서 차이가 같으면 재추출해도 평균이 안 변한다."""
    v = [0.2, 0.5, 0.9, 0.4]
    r = paired_bootstrap(arm(v), arm([x + 0.1 for x in v]), iters=2000)
    assert r.observed == pytest.approx(0.1)
    assert r.se == pytest.approx(0.0, abs=1e-12)


def test_MDE는_표준오차의_상수배다():
    rng = np.random.default_rng(0)
    a = arm(rng.random(30)); b = arm(rng.random(30))
    r = paired_bootstrap(a, b, iters=3000)
    assert r.mde == pytest.approx(MDE_MULTIPLIER * r.se)


def test_필요_표본은_효과의_제곱에_반비례한다():
    rng = np.random.default_rng(1)
    a = arm(rng.random(30)); b = arm(rng.random(30))
    r = paired_bootstrap(a, b, iters=3000)
    assert r.n_for(r.mde) == r.n
    # 효과가 절반이면 표본은 네 배
    assert r.n_for(r.mde / 2) == pytest.approx(4 * r.n, rel=0.02)


def test_군집_재추출은_군집을_통째로_뽑는다():
    rng = np.random.default_rng(2)
    a = arm(rng.random(12)); b = arm(rng.random(12))
    cl = {f"s{i}": f"alert{i // 4}" for i in range(12)}
    r = paired_bootstrap(a, b, cl, iters=2000)
    assert r.unit == "알림" and r.n_clusters == 3 and r.n == 12
