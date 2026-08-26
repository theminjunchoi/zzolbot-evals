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

_VOLATILE = (
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<uuid>"),
    (re.compile(r"\b[0-9a-f]{16,32}\b"), "<hex>"),
    (re.compile(r"\b\d{13}-\d+\b"), "<record>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}T[\d:.]+Z\b"), "<ts>"),
    (re.compile(r"joinCode=[A-Z0-9]{4}"), "joinCode=<code>"),
    (re.compile(r"\b(?:playerName|guestName)=\S+"), "player=<name>"),
    (re.compile(r"\b\d+\b"), "<n>"),
)


def normalize_message(message: str) -> str:
    for pattern, placeholder in _VOLATILE:
        message = pattern.sub(placeholder, message)
    return message.strip()


def signature(scenario: Scenario) -> tuple:
    """같은 문제인지 판단하는 뼈대. 알림과 (로거, 정규화된 메시지) 순서열로 정한다."""
    skeleton = []
    for line in scenario.log_samples:
        match = _LINE.match(line)
        if match:
            skeleton.append((match.group("logger"), normalize_message(match.group("message"))))
        else:
            skeleton.append(("?", normalize_message(line)))
    return (scenario.alert.alertname, tuple(skeleton))


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
