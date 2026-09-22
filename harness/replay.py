"""운영 Loki 로그를 그대로 시나리오로 만든다.

골든셋 33종은 내가 손으로 썼다. 깔끔한 한 줄짜리 로그만 들어 있고 스택 트레이스가 없다.
실제 운영 로그는 형태가 다르다(리포트 35번). 그 차이를 재려면 진짜 로그를 입력으로 써야 한다.

**왜 알림을 어긋나게 짝지은 케이스를 만드나.** 윈도우의 로그에서 알림을 유도하면 알림이 항상
로그와 맞는다. 그러면 양성 케이스만 생기고, 골든셋의 힘이 나온 음성 케이스(로그가 알림을
뒷받침하지 않는 경우)가 통째로 사라진다. 다른 윈도우의 에러로 알림을 만들어 짝지으면 로그는
진짜인 채로 **정답이 "근거 없음"인 케이스**가 구성으로 생긴다.

양성 케이스에는 라벨이 없다. 붙일 방법이 없어서다. 거기서는 두 모델의 일치율과 인용 접지율만
본다. 정답률을 잰다고 말하지 않는다.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from harness.domain import Alert, Scenario

WINDOW_SECONDS = 30 * 60
"""운영 설정과 같다(zzol-bot.monitor.error-log-window-minutes)."""

LOG_SAMPLE_LIMIT = 20
"""운영 설정과 같다(AlertEnrichmentService.LOG_SAMPLE_LIMIT)."""

MAX_STACK_FRAMES = 3
MAX_SAMPLE_LENGTH = 800
"""운영 LogSampleNormalizer 와 같은 값. 다르면 재생이 운영을 재현하지 못한다."""

_LEVEL_ERROR = re.compile(r"^\[[^\]]+\]\s+\[ERROR\s*\]")
_STACK_FRAME = re.compile(r"\s+at\s+[\w$.]+\([^)]*\)")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")
_LOGGER_AND_MESSAGE = re.compile(r"---\s+\[[^\]]*\]\s+(\S+)\s+:\s+(.*)")


@dataclass(frozen=True)
class LogLine:
    ts_ns: int
    line: str


@dataclass(frozen=True)
class Window:
    """ERROR 로그가 있는 30분 구간 하나."""

    index: int
    end_ns: int
    samples: tuple[str, ...]
    family: str


def load_lines(path: str | Path) -> list[LogLine]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            if not raw.strip():
                continue
            d = json.loads(raw)
            rows.append(LogLine(int(d["ts"]), d["line"]))
    rows.sort(key=lambda r: r.ts_ns)
    return rows


def is_error_level(line: str) -> bool:
    """레벨이 ERROR 인 줄만 근거가 된다.

    운영 쿼리는 줄 전체에서 ERROR 를 찾아 메시지에 그 글자가 든 INFO 까지 가져온다(#1820).
    재생에서는 그 줄들을 빼고 본다. 봇이 자기 로그를 근거로 읽은 결과를 재생해봐야 얻을 게 없다.
    """
    return bool(_LEVEL_ERROR.match(line))


def normalize(line: str) -> str:
    """운영 LogSampleNormalizer 를 그대로 옮긴 것. 두 구현이 갈라지면 재생이 운영과 달라진다."""
    line = _CONTROL.sub(" ", line)
    frames = list(_STACK_FRAME.finditer(line))
    if len(frames) > MAX_STACK_FRAMES:
        cut = frames[MAX_STACK_FRAMES]
        folded = len(frames) - MAX_STACK_FRAMES
        line = f"{line[: cut.start()]} ... (스택 {folded}줄 생략){line[frames[-1].end() :]}"
    if len(line) > MAX_SAMPLE_LENGTH:
        line = line[:MAX_SAMPLE_LENGTH] + " …(잘림)"
    return line


def family_of(line: str) -> str:
    """로그를 계열로 묶는다. 알림을 유도하고 음성 짝을 고를 때 쓴다."""
    m = _LOGGER_AND_MESSAGE.search(line)
    if not m:
        return "기타"
    logger, message = m.group(1), m.group(2)
    consumer = re.search(r"consumer=(\w+)", message)
    if consumer:
        return f"{logger}:{consumer.group(1)}"
    exception = re.search(r"exception=(\w+)", message)
    if exception:
        return f"{logger}:{exception.group(1)}"
    return logger


def build_windows(lines: list[LogLine]) -> list[Window]:
    """ERROR 로그가 하나라도 있는 30분 구간을 만든다. 구간은 겹치지 않는다."""
    errors = [r for r in lines if is_error_level(r.line)]
    buckets: dict[int, list[LogLine]] = {}
    for row in errors:
        buckets.setdefault(row.ts_ns // (WINDOW_SECONDS * 10**9), []).append(row)

    windows = []
    for i, (bucket, rows) in enumerate(sorted(buckets.items())):
        rows.sort(key=lambda r: r.ts_ns, reverse=True)
        kept = rows[:LOG_SAMPLE_LIMIT]
        samples = tuple(normalize(r.line) for r in kept)
        family = Counter(family_of(r.line) for r in kept).most_common(1)[0][0]
        windows.append(
            Window(index=i, end_ns=(bucket + 1) * WINDOW_SECONDS * 10**9, samples=samples, family=family)
        )
    return windows


COARSE_DESCRIPTIONS = {
    "c.global.redis.EventDispatcher": ("Redis Stream 컨슈머 처리 실패 급증", "이벤트 컨슈머가 메시지 처리에 반복 실패하고 있습니다."),
    "c.web.exception.RestExceptionHandler": ("HTTP 요청 처리 오류 급증", "REST 요청이 처리되지 못하고 오류로 끝나고 있습니다."),
    "c.r.i.w.PlayerDisconnectionService": ("플레이어 연결 종료 처리 실패 급증", "연결이 끊긴 플레이어의 정리 처리가 실패하고 있습니다."),
    "c.g.s.GameTaskSchedulerFactory": ("게임 스케줄러 오류 급증", "게임 진행 스케줄러가 작업을 예약하지 못하고 있습니다."),
}
"""굵은 계열을 사람이 쓸 법한 알림 문구로 옮긴다. 로거 클래스명을 알림에 노출하면 실제 알림과
모양이 달라지고, 모델이 로그와 알림을 클래스명으로 곧장 대조해버린다."""


def coarse_family(line_or_family: str) -> str:
    """컨슈머·예외 이름을 떼고 로거만 남긴다.

    음성 짝을 같은 로거 안에서 고르면 라벨이 흐려진다. 컨슈머 A 알림에 컨슈머 B 로그를 붙이면
    둘 다 "컨슈머 처리 실패"라 근거 없음이라고 단정할 수 없다. 짝은 굵은 계열이 다를 때만 만든다.
    """
    return line_or_family.split(":", 1)[0]


def _alert_for(coarse: str, index: int, matched: bool) -> Alert:
    """굵은 계열에서 알림을 만든다. 운영 룰(AppErrorLogSpike)의 모양을 따른다."""
    summary, description = COARSE_DESCRIPTIONS.get(coarse, (f"{coarse} 오류 급증", "오류가 임계를 초과했습니다."))
    return Alert(
        alertname="AppErrorLogSpike",
        severity="warning",
        fingerprint=f"replay-{'pos' if matched else 'neg'}-{index}",
        summary=summary,
        description=description,
        labels={"alertname": "AppErrorLogSpike", "severity": "warning", "job": "prod-app"},
    )


def to_scenarios(windows: list[Window]) -> list[Scenario]:
    """윈도우마다 양성 하나, 가능하면 음성 하나를 만든다.

    음성은 **그 윈도우에 없는 굵은 계열**의 알림을 붙인다. 로그는 진짜인데 알림과 무관하므로
    정답이 "근거 없음"이다. 굵게 잡는 이유는 같은 로거 안에서 짝지으면(컨슈머 A 알림 + 컨슈머 B
    로그) 둘 다 컨슈머 처리 실패라 근거 없음이라고 단정할 수 없기 때문이다.
    """
    coarse_all = sorted({coarse_family(w.family) for w in windows})
    scenarios: list[Scenario] = []
    for w in windows:
        present = {coarse_family(family_of(s)) for s in w.samples}
        scenarios.append(
            Scenario(
                name=f"replay-pos-{w.index:03d}",
                question="",
                rubric="",
                source="prod-replay",
                alert=_alert_for(coarse_family(w.family), w.index, matched=True),
                log_samples=w.samples,
                log_environment="prod",
                expected="",
            )
        )
        others = [f for f in coarse_all if f not in present]
        if not others:
            continue
        mismatched = others[w.index % len(others)]
        scenarios.append(
            Scenario(
                name=f"replay-neg-{w.index:03d}",
                question="",
                rubric="",
                source="prod-replay",
                alert=_alert_for(mismatched, w.index, matched=False),
                log_samples=w.samples,
                log_environment="prod",
                expected="아니오",
            )
        )
    return scenarios
