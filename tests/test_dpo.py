"""DPO 손실의 성질을 고정한다.

mlx-lm에 없어 직접 구현한 부분이라, 수식이 맞는지를 가짜 모델로 검증한다.
실제 모델을 쓰면 느리고 무엇이 틀렸는지 알 수 없다.
"""

from __future__ import annotations

import math

import mlx.core as mx
import pytest

from training.dpo import PreferencePair, completion_logprob, dpo_loss, implicit_accuracy


class FixedLogitsModel:
    """어떤 입력에도 같은 로짓을 내는 모델. 어휘 크기 4."""

    def __init__(self, logits_per_token: list[float]):
        self._row = mx.array(logits_per_token, dtype=mx.float32)

    def __call__(self, tokens):
        batch, length = tokens.shape
        return mx.broadcast_to(self._row, (batch, length, self._row.shape[0]))


def uniform_model():
    return FixedLogitsModel([0.0, 0.0, 0.0, 0.0])       # 균등분포. 토큰당 log(1/4)


def biased_model():
    return FixedLogitsModel([10.0, 0.0, 0.0, 0.0])      # 토큰 0을 강하게 선호


def pair(chosen, rejected, ref_c=0.0, ref_r=0.0):
    return PreferencePair(prompt=[1, 2], chosen=chosen, rejected=rejected,
                          ref_chosen_logp=ref_c, ref_rejected_logp=ref_r)


# --- 로그 확률 ---

def test_균등분포에서_로그확률은_토큰당_log_4분의1():
    lp = completion_logprob(uniform_model(), [1, 2], [3, 3, 3])
    assert float(lp.item()) == pytest.approx(3 * math.log(0.25), abs=1e-4)


def test_완성_길이에_비례한다():
    m = uniform_model()
    short = float(completion_logprob(m, [1, 2], [3]).item())
    long = float(completion_logprob(m, [1, 2], [3, 3]).item())
    assert long == pytest.approx(2 * short, abs=1e-4)


def test_프롬프트_길이는_로그확률에_영향을_주지_않는다():
    """프롬프트 토큰이 포함되면 긴 프롬프트가 손실을 지배한다."""
    m = uniform_model()
    a = float(completion_logprob(m, [1, 2], [3, 3]).item())
    b = float(completion_logprob(m, [1, 2, 1, 2, 1, 2], [3, 3]).item())
    assert a == pytest.approx(b, abs=1e-4)


def test_선호하는_토큰이_더_높은_로그확률을_받는다():
    m = biased_model()
    liked = float(completion_logprob(m, [1, 2], [0]).item())
    other = float(completion_logprob(m, [1, 2], [3]).item())
    assert liked > other


# --- 손실 ---

def test_정책과_참조가_같으면_손실은_log2():
    """마진이 0이면 -log sigmoid(0) = log 2."""
    m = uniform_model()
    ref = float(completion_logprob(m, [1, 2], [3]).item())
    loss = dpo_loss(m, pair([3], [3], ref_c=ref, ref_r=ref), beta=0.1)
    assert float(loss.item()) == pytest.approx(math.log(2), abs=1e-4)


def test_chosen을_더_선호하면_손실이_log2보다_작다():
    m = biased_model()
    p = pair(chosen=[0], rejected=[3])      # 모델이 0을 선호
    loss = float(dpo_loss(m, p, beta=0.1).item())
    assert loss < math.log(2)


def test_rejected를_더_선호하면_손실이_log2보다_크다():
    m = biased_model()
    p = pair(chosen=[3], rejected=[0])      # 뒤집힌 경우
    loss = float(dpo_loss(m, p, beta=0.1).item())
    assert loss > math.log(2)


def test_beta가_크면_같은_마진에서_손실이_더_민감하다():
    m = biased_model()
    p = pair(chosen=[0], rejected=[3])
    small = float(dpo_loss(m, p, beta=0.05).item())
    large = float(dpo_loss(m, p, beta=0.5).item())
    assert large < small          # 선호가 맞는 방향이면 beta가 클수록 손실이 더 내려간다


def test_손실은_항상_양수다():
    m = biased_model()
    for p in (pair([0], [3]), pair([3], [0]), pair([0], [0])):
        assert float(dpo_loss(m, p, beta=0.1).item()) > 0


def test_참조_로그확률이_마진을_상쇄한다():
    """참조도 chosen을 똑같이 선호하면 정책의 선호는 이득이 아니다."""
    m = biased_model()
    c = float(completion_logprob(m, [1, 2], [0]).item())
    r = float(completion_logprob(m, [1, 2], [3]).item())
    loss = dpo_loss(m, pair([0], [3], ref_c=c, ref_r=r), beta=0.1)
    assert float(loss.item()) == pytest.approx(math.log(2), abs=1e-4)


# --- 암묵 정확도 ---

def test_암묵_정확도는_마진_부호를_본다():
    m = biased_model()
    assert implicit_accuracy(m, pair([0], [3]))
    assert not implicit_accuracy(m, pair([3], [0]))
