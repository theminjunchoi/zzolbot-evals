"""판정 확률 추출.

모델은 `"evidenceFound": true` 또는 `false`를 낸다. **그 결정 토큰에서 로짓을 읽으면
확률이 나온다.** 학습이 필요 없다.

왜 필요한가. 이 프로젝트에서 개입할 때마다 반대편이 밀리는 일이 다섯 번 반복됐다
(리포트 18번). 원인 가설은 "모델에 근거를 얼마나 쉽게 인정하는가라는 임계값이 하나
있고 어떤 개입이든 그것을 움직인다"였다. 지금까지 각 팔은 곡선 위의 **한 점**이었고,
확률을 뽑으면 **곡선 전체**를 볼 수 있어 임계값 이동인지 판별 개선인지 갈린다.

부수 효과로 임계값이 **추론 시점 손잡이**가 된다. 원하는 트레이드오프 지점을 학습 없이
고를 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass

MARKER = '"evidenceFound":'


@dataclass(frozen=True)
class VerdictProbe:
    """판정 결정 토큰에서 true 확률을 잡는 로짓 프로세서.

    `"evidenceFound":` 가 나온 직후 한 번만 잡는다. 값이 이미 쓰였으면 지나간다.
    """

    tokenizer: object
    true_ids: tuple[int, ...]
    false_ids: tuple[int, ...]

    @classmethod
    def build(cls, tokenizer) -> "VerdictProbe":
        # 모델이 " true"처럼 앞 공백을 붙여 낼 수도 있어 두 형태를 다 받는다.
        def ids(text: str) -> tuple[int, ...]:
            out = []
            for piece in (text, " " + text):
                enc = tokenizer.encode(piece, add_special_tokens=False)
                if enc:
                    out.append(enc[0])
            return tuple(dict.fromkeys(out))

        return cls(tokenizer, ids("true"), ids("false"))

    def at_decision_point(self, generated: str) -> bool:
        """지금이 판정 값을 쓰기 직전인가."""
        at = generated.rfind(MARKER)
        if at == -1:
            return False
        rest = generated[at + len(MARKER):]
        return rest.strip() == ""      # 마커 뒤에 공백만 있으면 다음 토큰이 값이다


class ProbeCapture:
    """생성 중 판정 확률을 한 번 잡아 보관한다. mlx의 logits_processor 규약을 따른다."""

    def __init__(self, probe: VerdictProbe):
        self._probe = probe
        self.prob_true: float | None = None

    def __call__(self, tokens, logits):
        import mlx.core as mx

        if self.prob_true is not None:
            return logits
        ids = tokens.tolist() if hasattr(tokens, "tolist") else list(tokens)
        if not ids:
            return logits
        text = self._probe.tokenizer.decode(ids)
        if not self._probe.at_decision_point(text):
            return logits

        row = logits[0] if logits.ndim > 1 else logits
        probs = mx.softmax(row.astype(mx.float32))
        t = sum(float(probs[i].item()) for i in self._probe.true_ids)
        f = sum(float(probs[i].item()) for i in self._probe.false_ids)
        # true와 false에만 조건부로 정규화한다. 다른 토큰이 섞여도 판정 성향은 둘의 비다.
        self.prob_true = t / (t + f) if (t + f) > 0 else 0.5
        return logits


def roc_points(labels: list[bool], scores: list[float]) -> list[tuple[float, float, float]]:
    """(임계값, TPR, FPR)을 임계값 내림차순으로. sklearn 없이 계산한다."""
    pairs = sorted(zip(scores, labels), key=lambda x: -x[0])
    pos = sum(labels)
    neg = len(labels) - pos
    tp = fp = 0
    out = [(1.01, 0.0, 0.0)]
    for score, label in pairs:
        if label:
            tp += 1
        else:
            fp += 1
        out.append((score, tp / pos if pos else 0.0, fp / neg if neg else 0.0))
    return out


def auc(labels: list[bool], scores: list[float]) -> float:
    """ROC 아래 면적. 동점은 평균 순위로 처리한다(Mann-Whitney U와 같다)."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def best_threshold(labels: list[bool], scores: list[float]) -> tuple[float, float]:
    """Youden J(TPR - FPR)를 최대로 하는 임계값과 그때의 J."""
    best = (0.5, -1.0)
    for th, tpr, fpr in roc_points(labels, scores):
        j = tpr - fpr
        if j > best[1]:
            best = (th, j)
    return best
