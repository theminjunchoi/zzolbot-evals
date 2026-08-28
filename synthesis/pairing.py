"""대조 쌍 무결성 검사.

대조 쌍은 **로그를 고정하고 알림만 바꾼** 두 시나리오다. 로그가 같아야만 모델이
로그 표면 패턴으로 정답을 낼 수 없고, 알림과 로그의 관계를 봐야만 맞힐 수 있다.

생성기가 로그를 한 글자라도 바꾸면 그건 대조 쌍이 아니라 그냥 비슷한 시나리오 둘이다.
그러면 대조 학습의 전제가 조용히 무너진다. 그래서 바이트 단위 일치를 강제한다.

쌍은 이름으로 묶는다: `<공통이름>-a`, `<공통이름>-b`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

PAIR_SUFFIX = re.compile(r"^(?P<base>.+)-(?P<side>[ab])$")


def pair_key(name: str) -> tuple[str, str] | None:
    """`monitor-x-pair01-a` → (`monitor-x-pair01`, `a`). 쌍이 아니면 None."""
    match = PAIR_SUFFIX.match(name)
    if not match:
        return None
    return match.group("base"), match.group("side")


_TIMESTAMP = re.compile(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)")


def log_skeleton(line: str) -> str:
    """타임스탬프를 뗀 나머지. 시간 대조 쌍은 이것이 같아야 한다."""
    return _TIMESTAMP.sub("", line, count=1)


def span_minutes(lines: list[str]) -> float | None:
    """첫 로그와 마지막 로그의 시간 간격(분). 타임스탬프를 못 읽으면 None."""
    stamps = []
    for line in lines:
        match = _TIMESTAMP.match(line)
        if match:
            stamps.append(datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S"))
    if len(stamps) < 2:
        return None
    return (max(stamps) - min(stamps)).total_seconds() / 60


@dataclass(frozen=True)
class PairProblem:
    base: str
    reason: str


def check_temporal_pairs(candidates: list[dict], tight_max: float = 5.0,
                         spread_min: float = 60.0) -> list[PairProblem]:
    """시간 대조 쌍 검사.

    알림과 로그 **내용**을 고정하고 타임스탬프만 바꾼 쌍이다. 줄 수가 같으므로
    줄 수로는 둘을 구별할 수 없고, 시간 분포를 봐야만 맞힐 수 있다.

    모델이 "줄 수 대 알림 건수"의 비율로 판단하고 임계를 잘못 잡은 것이 관찰돼
    만든 유형이다(리포트 18번). 같은 알림, 같은 줄 수인데 10줄은 맞히고 8줄은 틀렸다.
    """
    groups: dict[str, dict[str, dict]] = {}
    for candidate in candidates:
        key = pair_key(candidate.get("name", ""))
        if key is None:
            continue
        base, side = key
        groups.setdefault(base, {})[side] = candidate

    problems = []
    for base, sides in sorted(groups.items()):
        if set(sides) != {"a", "b"}:
            problems.append(PairProblem(base, f"짝이 없다: {sorted(sides)}"))
            continue
        a, b = sides["a"], sides["b"]
        logs_a, logs_b = a.get("logSamples", []), b.get("logSamples", [])

        if len(logs_a) != len(logs_b):
            problems.append(PairProblem(
                base, f"줄 수가 다르다({len(logs_a)} 대 {len(logs_b)}). 줄 수로 구별되면 안 된다"))
            continue
        if [log_skeleton(x) for x in logs_a] != [log_skeleton(x) for x in logs_b]:
            problems.append(PairProblem(base, "타임스탬프 외의 내용이 다르다"))
            continue
        if a.get("expected") == b.get("expected"):
            problems.append(PairProblem(base, f"기대 판정이 같다({a.get('expected')})"))
            continue

        tight, spread = (a, b) if a.get("expected") == "예" else (b, a)
        st, ss = span_minutes(tight["logSamples"]), span_minutes(spread["logSamples"])
        if st is None or ss is None:
            problems.append(PairProblem(base, "타임스탬프를 읽을 수 없다"))
            continue
        if st > tight_max:
            problems.append(PairProblem(
                base, f"'예' 쪽이 {st:.1f}분에 퍼져 있다. {tight_max}분 이내여야 한다"))
        if ss < spread_min:
            problems.append(PairProblem(
                base, f"'아니오' 쪽이 {ss:.1f}분뿐이다. {spread_min}분 이상 흩어져야 한다"))
    return problems


def check_pairs(candidates: list[dict]) -> list[PairProblem]:
    """쌍 단위 문제를 전부 돌려준다. 개별 시나리오 검증은 기존 validators가 담당한다."""
    groups: dict[str, dict[str, dict]] = {}
    for candidate in candidates:
        key = pair_key(candidate.get("name", ""))
        if key is None:
            continue
        base, side = key
        groups.setdefault(base, {})[side] = candidate

    problems = []
    for base, sides in sorted(groups.items()):
        if set(sides) != {"a", "b"}:
            problems.append(PairProblem(base, f"짝이 없다: {sorted(sides)}"))
            continue
        a, b = sides["a"], sides["b"]

        if a.get("logSamples") != b.get("logSamples"):
            problems.append(PairProblem(base, "로그가 서로 다르다. 대조 쌍이 아니다"))
            continue
        if a.get("expected") == b.get("expected"):
            problems.append(PairProblem(
                base, f"기대 판정이 같다({a.get('expected')}). 대조가 성립하지 않는다"))
        alert_a, alert_b = a.get("alert", {}), b.get("alert", {})
        same_text = (alert_a.get("summary") == alert_b.get("summary")
                     and alert_a.get("description") == alert_b.get("description"))
        if same_text:
            problems.append(PairProblem(base, "알림 본문이 같다. 바뀐 것이 없다"))
        if a.get("logEnvironment") != b.get("logEnvironment"):
            problems.append(PairProblem(base, "로그 환경이 다르다. 알림 외 변수가 섞였다"))
    return problems


def paired_names(candidates: list[dict]) -> set[str]:
    """온전한 쌍을 이루는 시나리오 이름들. 문제가 있는 쌍은 제외한다."""
    bad = {p.base for p in check_pairs(candidates)}
    names = set()
    for candidate in candidates:
        key = pair_key(candidate.get("name", ""))
        if key and key[0] not in bad:
            names.add(candidate["name"])
    return names
