"""보상 함수의 배점을 고정한다.

이 값이 학습 신호이자 평가 종점이자 판정 기준이므로, 조용히 달라지면 세 가지가 한꺼번에
어긋난다. 항목별로 무엇이 몇 점인지 명시적으로 못박는다.
"""

from __future__ import annotations

import pytest

from analysis.reward import (
    CauseNamesEvidenceComponent,
    RewardFunction,
    RewardSpec,
    evidence_identifiers,
)
from harness.domain import Alert, Analysis, Scenario

DISPATCH_LINE = ("[2026-08-26 16:44:03.129] [ERROR] [1b8b3905222c1217,3d3def1565c045cb] "
                 "--- [redis-stream-thread-pool-laddergame1] c.global.redis.EventDispatcher : "
                 "이벤트 처리 실패: consumer=LadderDrawCommandEventConsumer, "
                 "message=LadderDrawCommandEvent[joinCode=V9KM]")

OUTBOX_LINE = ("[2026-08-26 17:06:58.443] [ERROR] [,] --- [pool-1-thread-2] "
               "c.global.outbox.OutboxEventProcessor : Outbox 이벤트 최대 재시도 초과, "
               "DEAD_LETTER 전환: id=6902, streamKey=minigame")


def scenario(expected: str, lines=(DISPATCH_LINE,)) -> Scenario:
    return Scenario(
        name="s", question="q", rubric="r", source="MANUAL",
        alert=Alert("A", "critical", "fp", "요약", "설명"),
        log_samples=lines, log_environment="prod", expected=expected)


def analysis(found=True, line=DISPATCH_LINE, cause="원인", summary="요약") -> Analysis:
    return Analysis(summary=summary, root_cause_hypothesis=cause,
                    suggested_actions=("조치",), evidence_found=found, evidence_line=line)


# --- 식별자 추출 ---

def test_로그에서_로거와_컨슈머와_스트림을_뽑는다():
    names = evidence_identifiers(DISPATCH_LINE)
    assert "EventDispatcher" in names
    assert "LadderDrawCommandEventConsumer" in names
    assert "laddergame" in names          # 스레드명에서 유도
    assert "c.global.redis.EventDispatcher" in names


def test_streamKey_표기도_뽑는다():
    names = evidence_identifiers(OUTBOX_LINE)
    assert "OutboxEventProcessor" in names
    assert "minigame" in names


def test_짧은_토큰은_식별자로_보지_않는다():
    assert all(len(n) >= 4 for n in evidence_identifiers(DISPATCH_LINE))


# --- 구체성 규칙 ---

def test_원인이_컴포넌트를_지목하면_통과():
    rule = CauseNamesEvidenceComponent()
    a = analysis(cause="LadderDrawCommandEventConsumer가 이벤트 처리에 실패하고 있다")
    assert rule.holds(scenario("예"), a)


def test_원인이_뭉뚱그리면_실패():
    rule = CauseNamesEvidenceComponent()
    a = analysis(cause="다운스트림 발행이 실패하고 있는 것으로 보인다")
    assert not rule.holds(scenario("예"), a)


def test_근거_없음이_정답이면_구체성은_해당_없음():
    rule = CauseNamesEvidenceComponent()
    assert rule.holds(scenario("아니오"), analysis(found=False, line="", cause=""))


# --- 배점 ---

def test_완벽한_양성_답변은_만점():
    r = RewardFunction().score(
        scenario("예"),
        analysis(cause="LadderDrawCommandEventConsumer 처리 실패", line=DISPATCH_LINE))
    assert r.total == pytest.approx(1.0)


def test_기본_배점은_구체성을_빼고_1점이_된다():
    """사전 등록 검사에서 구체성 규칙이 탈락했으므로 기본 가중치가 0이다."""
    spec = RewardSpec()
    assert spec.specificity == 0.0
    assert spec.schema + spec.verdict + spec.citation == pytest.approx(1.0)


def test_완벽한_음성_답변도_만점():
    """근거 없음이 정답인 시나리오에서 인용과 구체성은 해당 없으므로 만점 처리한다."""
    r = RewardFunction().score(
        scenario("아니오"),
        Analysis("근거를 찾지 못했다", "", ("조치",), False, ""))
    assert r.total == pytest.approx(1.0)


def test_판정이_틀리면_판정_배점만_잃는다():
    spec = RewardSpec()
    r = RewardFunction(spec).score(
        scenario("아니오"),
        analysis(found=True, cause="LadderDrawCommandEventConsumer 실패"))
    assert r.parts["verdict"] == 0.0
    assert r.parts["schema"] == spec.schema


def test_인용이_원문과_다르면_인용_배점을_잃는다():
    broken = DISPATCH_LINE.replace("16:44:03.129", "16:44:03.130")
    r = RewardFunction().score(scenario("예"), analysis(line=broken, cause="EventDispatcher 실패"))
    assert r.parts["citation"] == 0.0
    assert r.parts["verdict"] > 0.0     # 판정은 맞았다


def test_근거_없음인데_원인을_말하면_감점():
    spec = RewardSpec()
    r = RewardFunction(spec).score(
        scenario("아니오"),
        Analysis("요약", "디스크가 찼다", ("조치",), False, ""))
    assert r.parts["penalty"] == pytest.approx(-spec.cause_without_evidence_penalty)


def test_파싱_실패는_0점이고_표시가_남는다():
    r = RewardFunction().score(scenario("예"), None)
    assert r.total == 0.0
    assert r.parse_failed


def test_구체성을_켜면_뭉뚱그린_원인이_감점된다():
    """규칙은 진단용으로 남아 있어 가중치를 주면 동작한다."""
    spec = RewardSpec(schema=0.1, verdict=0.4, citation=0.3, specificity=0.2)
    r = RewardFunction(spec).score(scenario("예"), analysis(cause="뭉뚱그린 원인"))
    assert r.parts["specificity"] == 0.0
    assert r.total == pytest.approx(0.8)
