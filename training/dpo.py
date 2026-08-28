"""DPO(Direct Preference Optimization) 손실과 학습 루프.

mlx-lm에는 SFT 손실만 있어 직접 구현한다.

**왜 DPO인가.** 남은 실패가 과소(근거 미주장)와 과잉(오탐)으로 동시에 있다. 이건 결정
경계 문제다. SFT는 모방이라 좋은 출력의 확률을 올릴 뿐 나쁜 출력을 명시적으로 누르지
않는다. DPO는 같은 입력에 대해 좋은 것과 나쁜 것을 대비시켜 경계에 직접 작용한다.

**선호 라벨을 사람이 아니라 코드가 매긴다.** chosen은 검증을 통과한 교사 출력,
rejected는 모델이 뽑은 최저 보상 샘플이다. 모델이 한 번도 맞히지 못하는 프롬프트에서도
chosen이 존재하므로, 가장 어려운 경계를 건너뛰지 않는다. RLHF 알고리즘 위에서 RLVR을
하는 셈이다.

손실:

    L = -log sigmoid( beta * [ (logp_policy(chosen) - logp_ref(chosen))
                             - (logp_policy(rejected) - logp_ref(rejected)) ] )

로그 확률은 **완성 토큰에만** 계산한다. 프롬프트 부분을 포함하면 프롬프트가 긴 샘플이
손실을 지배한다.

참조 로그 확률은 미리 계산해 둔다. 그러면 학습 중 참조 모델을 메모리에 들 필요가 없고
스텝당 forward가 4회에서 2회로 준다.
"""

from __future__ import annotations

from dataclasses import dataclass

import mlx.core as mx
import mlx.nn as nn


@dataclass(frozen=True)
class PreferencePair:
    """한 프롬프트에 대한 선호 쌍. 토큰 id로 들고 있어 학습 중 토큰화가 없다."""

    prompt: list[int]
    chosen: list[int]
    rejected: list[int]
    ref_chosen_logp: float = 0.0
    ref_rejected_logp: float = 0.0

    def with_reference(self, chosen_logp: float, rejected_logp: float) -> "PreferencePair":
        return PreferencePair(self.prompt, self.chosen, self.rejected, chosen_logp, rejected_logp)


def completion_logprob(model, prompt: list[int], completion: list[int]) -> mx.array:
    """완성 토큰들의 로그 확률 합. 프롬프트 부분은 제외한다.

    입력은 prompt+completion이고, 위치 i의 로짓이 위치 i+1의 토큰을 예측하므로
    완성의 첫 토큰을 예측하는 로짓은 프롬프트의 마지막 위치에 있다.
    """
    tokens = mx.array([prompt + completion])
    logits = model(tokens[:, :-1]).astype(mx.float32)
    targets = tokens[:, 1:]

    start = len(prompt) - 1          # 완성 첫 토큰을 예측하는 위치
    logits = logits[:, start:, :]
    targets = targets[:, start:]

    logprobs = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
    picked = mx.take_along_axis(logprobs, targets[..., None], axis=-1).squeeze(-1)
    return picked.sum()


def dpo_loss(model, pair: PreferencePair, beta: float = 0.1) -> mx.array:
    """쌍 하나의 DPO 손실. 참조 로그 확률은 이미 계산돼 있어야 한다."""
    policy_chosen = completion_logprob(model, pair.prompt, pair.chosen)
    policy_rejected = completion_logprob(model, pair.prompt, pair.rejected)

    chosen_margin = policy_chosen - pair.ref_chosen_logp
    rejected_margin = policy_rejected - pair.ref_rejected_logp
    logits = beta * (chosen_margin - rejected_margin)
    # -log sigmoid(x) = softplus(-x). 큰 음수에서 안정적이다.
    return mx.logaddexp(mx.array(0.0), -logits)


def implicit_accuracy(model, pair: PreferencePair) -> bool:
    """정책이 chosen을 rejected보다 선호하는가. 손실과 별개로 봐야 진척이 보인다."""
    chosen = completion_logprob(model, pair.prompt, pair.chosen) - pair.ref_chosen_logp
    rejected = completion_logprob(model, pair.prompt, pair.rejected) - pair.ref_rejected_logp
    return bool((chosen > rejected).item())


def precompute_reference(model, pairs: list[PreferencePair]) -> list[PreferencePair]:
    """참조 정책(어댑터를 끈 상태)의 로그 확률을 미리 계산한다.

    호출 전에 모델의 LoRA 어댑터가 꺼져 있어야 한다. 켜진 채로 부르면 참조가 정책과
    같아져 마진이 0이 되고 DPO가 아무것도 학습하지 않는다.
    """
    out = []
    for pair in pairs:
        chosen = completion_logprob(model, pair.prompt, pair.chosen)
        rejected = completion_logprob(model, pair.prompt, pair.rejected)
        mx.eval(chosen, rejected)
        out.append(pair.with_reference(float(chosen.item()), float(rejected.item())))
    return out


def train_step(model, optimizer, pair: PreferencePair, beta: float) -> float:
    loss_and_grad = nn.value_and_grad(model, lambda m: dpo_loss(m, pair, beta))
    loss, grads = loss_and_grad(model)
    optimizer.update(model, grads)
    mx.eval(model.parameters(), optimizer.state, loss)
    return float(loss.item())
