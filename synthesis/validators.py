"""합성 후보에 대한 실행 가능한 정확성 계약.

각 검증기는 위반 사유 목록을 돌려준다. 새 검증은 Validator 구현을 추가해 끼운다.
손으로 검증한 기존 골든셋 20종이 전부 통과해야 이 필터 자체가 올바른 것이다
(tests/test_validators.py가 그 자가 검증이다).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import Counter
from datetime import datetime

from synthesis.catalog import (
    ALERT_RULES,
    ALERT_TEXT_TEMPLATES,
    LOG_MESSAGES,
    LOGGER_THREAD_AFFINITY,
    STREAM_POOL_NAMES,
    THREAD_PATTERNS,
)

LOG_LINE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\] "
    r"\[(?P<level>ERROR|WARN)\] "
    r"\[(?P<trace>[0-9a-f]{32})?,(?P<span>[0-9a-f]{16})?\] --- "
    r"\[(?P<thread>[^\]]*)\] "
    r"(?P<logger>\S+) : "
    r"(?P<message>.+)$"
)

REQUIRED_FIELDS = ("name", "question", "rubric", "source", "alert", "logSamples", "logEnvironment")


def _template_to_regex(template: str) -> re.Pattern:
    parts = [re.escape(part) for part in template.split("{}")]
    return re.compile("^" + ".+?".join(parts).replace(re.escape("{}"), ".+?") + "$", re.DOTALL)


MESSAGE_REGEXES = tuple((m, _template_to_regex(m.template)) for m in LOG_MESSAGES)

_STREAM_THREAD = re.compile(r"redis-stream-thread-pool-([a-z:]+)\d+")


def _thread_family(thread: str) -> str | None:
    """스레드명을 실행 경로 계열로 분류한다. 미상이면 None."""
    if thread == "":
        return "virtual"
    if re.fullmatch(r"http-nio-8080-exec-\d+", thread):
        return "exec"
    stream = _STREAM_THREAD.fullmatch(thread)
    if stream:
        return "stream" if stream.group(1) in STREAM_POOL_NAMES else None
    if re.fullmatch(r"pool-\d+-thread-\d+", thread) or re.fullmatch(r"delay-removal-task-\d+", thread):
        return "pool"
    if re.fullmatch(r"[a-z]+-task-\d+", thread):
        return "game-task"
    if re.fullmatch(r"clientInboundChannel-\d+", thread):
        return "ws-inbound"
    return None


class Validator(ABC):
    name: str

    @abstractmethod
    def violations(self, candidate: dict) -> list[str]: ...


class SchemaValidator(Validator):
    name = "schema"

    def violations(self, candidate: dict) -> list[str]:
        found = [f"필수 필드 누락: {k}" for k in REQUIRED_FIELDS if k not in candidate]
        if found:
            return found
        if not isinstance(candidate["logSamples"], list) or not candidate["logSamples"]:
            found.append("logSamples는 비어 있지 않은 배열이어야 함")
        if candidate["logEnvironment"] != "prod":
            found.append(f"logEnvironment는 prod여야 함: {candidate['logEnvironment']}")
        if not re.fullmatch(r"monitor-[a-z0-9-]+", candidate["name"]):
            found.append(f"name 형식 위반: {candidate['name']}")
        return found


class AlertValidator(Validator):
    name = "alert"

    def violations(self, candidate: dict) -> list[str]:
        alert = candidate.get("alert") or {}
        found = []
        rule = ALERT_RULES.get(alert.get("alertname", ""))
        if rule is None:
            return [f"존재하지 않는 알림: {alert.get('alertname')}"]
        if alert.get("severity") != rule.severity:
            found.append(f"{rule.alertname} severity는 {rule.severity}여야 함: {alert.get('severity')}")
        labels = alert.get("labels") or {}
        for key, value in rule.required_labels.items():
            if labels.get(key) != value:
                found.append(f"라벨 {key}={value} 필요: {labels.get(key)}")
        allowed = {"alertname", "severity", *rule.required_labels, *rule.optional_labels}
        for key in labels:
            if key not in allowed:
                found.append(f"{rule.alertname}에 없는 라벨: {key}")
        if not alert.get("summary") or not alert.get("description"):
            found.append("summary/description 누락")
        return found


class LogLineValidator(Validator):
    """모든 로그 라인이 실제 파일 로그 패턴과 일치하고, 로거/스레드/메시지가 실코드에 실존해야 한다."""

    name = "log-line"

    def violations(self, candidate: dict) -> list[str]:
        found = []
        for i, line in enumerate(candidate.get("logSamples") or []):
            match = LOG_LINE.match(line)
            if not match:
                found.append(f"로그 {i}: 파일 로그 패턴 불일치")
                continue
            level, thread = match.group("level"), match.group("thread")
            logger, message = match.group("logger"), match.group("message")
            family = _thread_family(thread)
            if not any(re.fullmatch(p, thread) for p in THREAD_PATTERNS) or family is None:
                found.append(f"로그 {i}: 실존하지 않는 스레드명: {thread}")
            matched = [m for m, rx in MESSAGE_REGEXES if m.logger == logger and rx.match(message)]
            if not matched:
                found.append(f"로그 {i}: 카탈로그에 없는 로거/메시지: {logger} : {message[:60]}")
                continue
            if all(m.level != level for m in matched):
                found.append(f"로그 {i}: 레벨 불일치({level}): {message[:60]}")
            affinity = LOGGER_THREAD_AFFINITY.get(logger)
            if affinity and family is not None and family not in affinity:
                found.append(f"로그 {i}: {logger}는 {affinity} 스레드에서 돌지만 {family}({thread})에 있음")
        return found


class AlertTextValidator(Validator):
    """summary와 description이 실제 룰 annotation 템플릿의 렌더 형태여야 한다."""

    name = "alert-text"

    def violations(self, candidate: dict) -> list[str]:
        alert = candidate.get("alert") or {}
        templates = ALERT_TEXT_TEMPLATES.get(alert.get("alertname", ""))
        if templates is None:
            return []  # 알림 자체가 없으면 AlertValidator가 잡는다
        summary_templates, description_templates = templates
        found = []
        if not any(_template_to_regex(t).match(alert.get("summary") or "") for t in summary_templates):
            found.append(f"summary가 룰 템플릿과 다름: {alert.get('summary')}")
        if not any(_template_to_regex(t).match(alert.get("description") or "") for t in description_templates):
            found.append(f"description이 룰 템플릿과 다름: {(alert.get('description') or '')[:80]}")
        return found


class TimestampValidator(Validator):
    """시각이 파싱 가능하고 오름차순이어야 한다. 창 정합 여부는 축(axis)의 의도이므로
    expected 메타와 함께 CoherenceValidator가 본다."""

    name = "timestamp"

    def violations(self, candidate: dict) -> list[str]:
        stamps = []
        for i, line in enumerate(candidate.get("logSamples") or []):
            match = LOG_LINE.match(line)
            if not match:
                continue
            try:
                stamps.append(datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S.%f"))
            except ValueError:
                return [f"로그 {i}: 시각 파싱 불가"]
        if stamps != sorted(stamps):
            return ["로그 시각이 오름차순이 아님"]
        return []


class RubricValidator(Validator):
    """rubric이 flatten 계약 문자열을 인용하고, 후보의 expected 메타와 방향이 일치해야 한다."""

    name = "rubric"

    def violations(self, candidate: dict) -> list[str]:
        rubric = candidate.get("rubric") or ""
        found = []
        has_yes = "근거 발견: 예" in rubric
        has_no = "근거 발견: 아니오" in rubric
        if not has_yes and not has_no:
            found.append("rubric이 '근거 발견: 예/아니오'를 인용하지 않음")
        if "정답" not in rubric or "오답" not in rubric:
            found.append("rubric에 정답/오답 조건이 없음")
        expected = candidate.get("expected")
        if expected == "예" and not has_yes:
            found.append("expected=예인데 rubric이 '근거 발견: 예'를 정답으로 인용하지 않음")
        if expected == "아니오" and not has_no:
            found.append("expected=아니오인데 rubric이 '근거 발견: 아니오'를 정답으로 인용하지 않음")
        return found


class DuplicateNameValidator(Validator):
    name = "duplicate"

    def __init__(self, existing_names: set[str]):
        self._existing = set(existing_names)

    def violations(self, candidate: dict) -> list[str]:
        if candidate.get("name") in self._existing:
            return [f"이름 중복: {candidate.get('name')}"]
        return []


def default_validators(existing_names: set[str] | None = None) -> list[Validator]:
    return [
        SchemaValidator(),
        AlertValidator(),
        AlertTextValidator(),
        LogLineValidator(),
        TimestampValidator(),
        RubricValidator(),
        DuplicateNameValidator(existing_names or set()),
    ]


class FilterStats:
    """검증기별 탈락 건수와 사유를 집계한다. 합성 리포트의 '필터별 탈락률' 표가 여기서 나온다."""

    def __init__(self):
        self.total = 0
        self.passed = 0
        self.dropped_by: Counter[str] = Counter()
        self.reasons: list[tuple[str, str, list[str]]] = []

    def record(self, candidate_name: str, failures: dict[str, list[str]]) -> bool:
        self.total += 1
        if not any(failures.values()):
            self.passed += 1
            return True
        for validator_name, reasons in failures.items():
            if reasons:
                self.dropped_by[validator_name] += 1
                self.reasons.append((candidate_name, validator_name, reasons))
        return False


def validate(candidate: dict, validators: list[Validator]) -> dict[str, list[str]]:
    return {v.name: v.violations(candidate) for v in validators}
