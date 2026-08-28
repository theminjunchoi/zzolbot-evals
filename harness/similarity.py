"""시나리오의 내용 동일성 판단.

이름이 달라도 같은 문제인 경우가 있다. 타임스탬프와 트레이스 ID, joinCode 같은 값은 매번
다르지만 그건 표면이고, 문제를 정하는 것은 어떤 알림에 어떤 로거의 어떤 메시지가 어떤 순서로
주어지는가다. 그래서 값을 자리표시자로 지운 뒤 남는 뼈대를 시그니처로 삼는다.

학습 데이터에서 이게 중요한 이유는 세 가지다.
- 같은 문제가 여러 번 들어가면 그 패턴에 과적합한다.
- train과 valid에 같은 문제가 갈리면 valid 손실이 학습 진척을 재지 못한다.
- 평가 골든셋과 겹치면 평가 자체가 무의미해진다.
"""

from __future__ import annotations

import re

from harness.domain import Scenario

_LINE = re.compile(r"^\[[^\]]*\] \[[A-Z]+\] \[[^\]]*\] --- \[[^\]]*\] (?P<logger>\S+) : (?P<message>.+)$")

# 실행마다 달라지는 식별자. 이것만 지우면 "같은 문제"의 뼈대가 남는다.
_VOLATILE_IDS = (
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<uuid>"),
    (re.compile(r"\b[0-9a-f]{16,32}\b"), "<hex>"),
    (re.compile(r"\b\d{13}-\d+\b"), "<record>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}T[\d:.]+Z\b"), "<ts>"),
    (re.compile(r"joinCode=[A-Z0-9]{4}"), "joinCode=<code>"),
    (re.compile(r"\b(?:playerName|guestName)=\S+"), "player=<name>"),
)

# 로그 본문의 남은 숫자(건수, id, 인덱스)까지 지운다. 알림 본문에는 적용하지 않는데,
# 알림이 말하는 규모(5분에 50건 대 5분에 5건)는 문제를 가르는 정보이기 때문이다.
_VOLATILE_NUMBERS = ((re.compile(r"\b\d+\b"), "<n>"),)

_VOLATILE = _VOLATILE_IDS + _VOLATILE_NUMBERS


def _apply(patterns, text: str) -> str:
    for pattern, placeholder in patterns:
        text = pattern.sub(placeholder, text)
    return text.strip()


def normalize_message(message: str) -> str:
    """로그 본문 정규화. 식별자와 숫자를 모두 지운다."""
    return _apply(_VOLATILE, message)


def normalize_alert_text(text: str) -> str:
    """알림 본문 정규화. 식별자만 지우고 숫자는 남긴다."""
    return _apply(_VOLATILE_IDS, text)


def span_bucket(lines: tuple[str, ...] | list[str]) -> str:
    """로그가 몇 분에 걸쳐 있는지의 구간. 정확한 분이 아니라 구간으로 잡는다.

    같은 문제가 우연히 몇 초 다른 것까지 다르다고 보면 중복 탐지가 무력해진다.
    """
    from synthesis.pairing import span_minutes

    span = span_minutes(list(lines))
    if span is None:
        return "?"
    if span <= 5:
        return "tight"
    if span <= 60:
        return "mid"
    return "spread"


def signature(scenario: Scenario) -> tuple:
    """같은 문제인지 판단하는 뼈대.

    **대조가 바꾸는 축은 반드시 뼈대에 들어가야 한다.** 안 그러면 대조 쌍이 중복으로
    판정돼 학습 데이터에서 통째로 탈락한다. 세 번 겪었다.

    - 알림 대조 쌍(로그 고정, 알림 변경) → 알림 요약과 설명을 넣음
    - 시간 대조 쌍(내용 고정, 타임스탬프 변경) → 로그의 시간 구간을 넣음
    """
    skeleton = []
    for line in scenario.log_samples:
        match = _LINE.match(line)
        if match:
            skeleton.append((match.group("logger"), normalize_message(match.group("message"))))
        else:
            skeleton.append(("?", normalize_message(line)))
    alert = scenario.alert
    return (
        alert.alertname,
        normalize_alert_text(alert.summary),
        normalize_alert_text(alert.description),
        span_bucket(scenario.log_samples),
        tuple(skeleton),
    )


def find_duplicates(scenarios: list[Scenario],
                    against: list[Scenario] | None = None) -> list[tuple[str, str]]:
    """중복 쌍을 (뒤에 온 것, 먼저 있던 것)으로 돌려준다.

    against를 주면 그쪽과 겹치는 것만 본다(평가셋 대조용).
    """
    seen: dict[tuple, str] = {}
    for scenario in (against or []):
        seen.setdefault(signature(scenario), scenario.name)
    pairs = []
    for scenario in scenarios:
        key = signature(scenario)
        if key in seen:
            pairs.append((scenario.name, seen[key]))
        else:
            seen[key] = scenario.name
    return pairs
