"""판정 확률 추출과 ROC 계산을 고정한다.

결정 지점을 잘못 잡으면 엉뚱한 토큰의 확률을 읽는다. 로짓을 읽는 코드라
눈으로 확인하기 어려우므로 가짜 토크나이저로 못박는다.
"""

from __future__ import annotations

import pytest

from analysis.verdict_prob import VerdictProbe, auc, best_threshold, roc_points


class CharTokenizer:
    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        return [ord(c) for c in text]

    def decode(self, ids) -> str:
        return "".join(chr(i) for i in ids)


def probe() -> VerdictProbe:
    return VerdictProbe.build(CharTokenizer())


# --- 결정 지점 판정 ---

def test_마커_직후가_결정_지점이다():
    assert probe().at_decision_point('{"evidenceFound":')
    assert probe().at_decision_point('{"evidenceFound": ')


def test_마커_전에는_결정_지점이_아니다():
    assert not probe().at_decision_point('{"summary": "무언가"')


def test_값이_이미_쓰였으면_지나간다():
    assert not probe().at_decision_point('{"evidenceFound": true')
    assert not probe().at_decision_point('{"evidenceFound": false, "x"')


def test_마커가_여러_번_나오면_마지막을_본다():
    assert probe().at_decision_point('{"evidenceFound": true} {"evidenceFound":')


# --- ROC ---

def test_완벽한_분리는_auc_1():
    labels = [True, True, False, False]
    assert auc(labels, [0.9, 0.8, 0.2, 0.1]) == pytest.approx(1.0)


def test_뒤집힌_분리는_auc_0():
    labels = [True, True, False, False]
    assert auc(labels, [0.1, 0.2, 0.8, 0.9]) == pytest.approx(0.0)


def test_전부_같은_점수면_auc_반():
    labels = [True, True, False, False]
    assert auc(labels, [0.5] * 4) == pytest.approx(0.5)


def test_한쪽_라벨만_있으면_nan():
    import math
    assert math.isnan(auc([True, True], [0.9, 0.8]))


def test_roc는_임계값_내림차순이다():
    pts = roc_points([True, False, True], [0.9, 0.5, 0.1])
    assert pts[0] == (1.01, 0.0, 0.0)
    assert [p[0] for p in pts[1:]] == [0.9, 0.5, 0.1]


def test_최적_임계값은_youden_J를_최대로_한다():
    labels = [True, True, False, False]
    th, j = best_threshold(labels, [0.9, 0.8, 0.2, 0.1])
    assert j == pytest.approx(1.0)
    assert th == pytest.approx(0.8)


def test_임계값이_같은_점을_지나면_동점_처리():
    """같은 확률에 양성과 음성이 섞이면 완벽 분리가 아니다."""
    assert auc([True, False], [0.5, 0.5]) == pytest.approx(0.5)
