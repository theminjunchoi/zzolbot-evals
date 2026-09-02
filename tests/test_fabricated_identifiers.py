"""환각 검사의 범위를 고정한다.

기존 `IdentifiersAreGrounded`와 조작적 정의는 같고 **보는 필드만 다르다.**
그 차이가 이 규칙의 존재 이유이므로 거기를 못박는다.

**이 규칙은 식별자 수준의 환각만 잡는다.** 메커니즘을 순수 한국어로 지어내는 오진은
식별자가 전부 맞아도 성립하고 못 잡는다. 실측으로 확인했으므로 테스트로도 고정한다.
"""

from __future__ import annotations

from harness.domain import Alert, Analysis, Scenario
from training.verification import IdentifiersAreGrounded, NoFabricatedIdentifiers

LOG = ("[2026-08-26 14:00:05.112] [ERROR] [t,s] --- [redis-stream-thread-pool-room] "
       "c.g.h.RoomJoinConsumer : 방 참가 이벤트 처리 실패 streamKey=room:join")


def scenario() -> Scenario:
    return Scenario(
        name="t", question="q", rubric="근거 발견: 예", source="t",
        alert=Alert(alertname="AppErrorLogSpike", severity="warning", fingerprint="f",
                    summary="에러 급증", description="prod-app 에러 급증", labels={"job": "prod-app"}),
        log_samples=(LOG,), log_environment="prod-app", expected="예")


def answer(cause: str = "", actions: tuple[str, ...] = ()) -> Analysis:
    return Analysis(summary="에러가 급증했다", root_cause_hypothesis=cause,
                    suggested_actions=actions, evidence_found=True,
                    evidence_line=LOG, grounded=True)


def test_로그에_있는_이름은_통과한다():
    a = answer("RoomJoinConsumer 처리 실패", ("RoomJoinConsumer 로그를 확인",))
    assert NoFabricatedIdentifiers().violations(scenario(), a) == []


def test_조치_필드의_지어낸_이름을_잡는다():
    """기존 규칙과 갈리는 지점이다. 기존은 조치를 안 본다."""
    a = answer("RoomJoinConsumer 처리 실패", ("RoomJoinEventConsumer 를 재시작",))
    assert NoFabricatedIdentifiers().violations(scenario(), a) != []
    assert IdentifiersAreGrounded().violations(scenario(), a) == []


def test_원인_필드는_두_규칙_다_잡는다():
    a = answer("RoomJoinEventConsumer 처리 실패")
    assert NoFabricatedIdentifiers().violations(scenario(), a) != []
    assert IdentifiersAreGrounded().violations(scenario(), a) != []


def test_식별자_없는_메커니즘_날조는_못_잡는다():
    """**이 규칙의 한계를 고정한다.** 변형 프로브의 component-swap이 정확히 이 형태라
    검출 0/14가 나왔다. 나중에 이걸 잡게 고치려면 조작적 정의부터 바꿔야 한다."""
    a = answer("프론트엔드 정적 파일 캐시 무효화 실패로 인해 발생한 것으로 보입니다.")
    assert NoFabricatedIdentifiers().violations(scenario(), a) == []


def test_일반_한국어_조치는_잡지_않는다():
    a = answer("RoomJoinConsumer 처리 실패",
               ("연결 풀 설정을 확인하세요", "재시도 정책을 검토하세요"))
    assert NoFabricatedIdentifiers().violations(scenario(), a) == []
