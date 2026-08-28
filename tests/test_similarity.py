"""시그니처가 무엇을 같다고 보고 무엇을 다르다고 보는지 고정한다.

대조 쌍(로그를 고정하고 알림만 바꾼 쌍)은 서로 다른 문제여야 한다. 시그니처가 이를
중복으로 판정하면 학습 데이터에서 통째로 탈락한다.
"""

from __future__ import annotations

from dataclasses import replace

from harness.domain import Alert, Scenario
from harness.similarity import find_duplicates, normalize_alert_text, normalize_message, signature

LINE_A = ("[2026-08-26 14:10:05.123] [ERROR] [a1b2c3d4e5f60708090a1b2c3d4e5f60,b2c3d4e5f6070809] "
          "--- [redis-stream-thread-pool-laddergame1] c.global.redis.EventDispatcher : "
          "이벤트 처리 실패: consumer=LadderDrawCommandEventConsumer, message=LadderDrawCommandEvent"
          "[eventId=5d24f7ae-982b-43ef-b556-01af13674306, joinCode=V9KM, playerName=PLAYER_1]")


def scenario(name: str, alertname: str, summary: str, description: str,
             lines: tuple[str, ...] = (LINE_A,)) -> Scenario:
    return Scenario(
        name=name,
        question="질문",
        rubric="채점 기준",
        source="MANUAL",
        alert=Alert(alertname=alertname, severity="critical", fingerprint="fp",
                    summary=summary, description=description),
        log_samples=lines,
        log_environment="prod",
    )


def test_같은_문제는_휘발성_값이_달라도_같다():
    a = scenario("a", "RedisStreamBacklogHigh", "적체", "laddergame 스트림 적체")
    other_line = LINE_A.replace("V9KM", "PXMH").replace("PLAYER_1", "PLAYER_9")
    b = scenario("b", "RedisStreamBacklogHigh", "적체", "laddergame 스트림 적체", (other_line,))
    assert signature(a) == signature(b)


def test_대조_쌍은_알림명이_같아도_다른_문제다():
    """로그가 완전히 같고 알림 대상만 다른 쌍. 이것이 중복으로 잡히면 대조 학습이 불가능하다."""
    a = scenario("a", "RedisStreamBacklogHigh", "laddergame 적체", "laddergame 스트림이 적체됐다")
    b = scenario("b", "RedisStreamBacklogHigh", "room:join 적체", "room:join 스트림이 적체됐다")
    assert a.log_samples == b.log_samples
    assert signature(a) != signature(b)
    assert find_duplicates([a, b]) == []


def test_알림명이_다르면_당연히_다르다():
    a = scenario("a", "RedisStreamBacklogHigh", "적체", "설명")
    b = scenario("b", "DiskUsageHigh", "적체", "설명")
    assert signature(a) != signature(b)


def test_알림의_규모는_구분한다():
    """5분에 50건과 5분에 5건은 양적 정합성이 갈리는 서로 다른 문제다."""
    a = scenario("a", "ErrorSpike", "에러 급증", "최근 5분간 50건 발생")
    b = scenario("b", "ErrorSpike", "에러 급증", "최근 5분간 5건 발생")
    assert signature(a) != signature(b)


def test_로그_본문의_숫자는_구분하지_않는다():
    """로그의 id나 건수는 실행마다 달라지는 표면 값이다."""
    a = scenario("a", "OutboxHigh", "적체", "설명",
                 ("[2026-08-26 14:10:05.123] [ERROR] [,] --- [pool-1-thread-2] "
                  "c.global.outbox.OutboxEventProcessor : DEAD_LETTER 전환: id=6902",))
    b = scenario("b", "OutboxHigh", "적체", "설명",
                 ("[2026-08-26 15:22:41.900] [ERROR] [,] --- [pool-3-thread-9] "
                  "c.global.outbox.OutboxEventProcessor : DEAD_LETTER 전환: id=1177",))
    assert signature(a) == signature(b)


def test_로그_순서가_다르면_다른_문제다():
    line_b = LINE_A.replace("laddergame1", "nunchi1").replace(
        "LadderDrawCommandEventConsumer", "NunchiCommandEventConsumer")
    a = scenario("a", "X", "s", "d", (LINE_A, line_b))
    b = scenario("b", "X", "s", "d", (line_b, LINE_A))
    assert signature(a) != signature(b)


def test_against를_주면_그쪽과만_대조한다():
    a = scenario("a", "X", "s", "d")
    b = scenario("b", "X", "s", "d")
    assert find_duplicates([b], against=[a]) == [("b", "a")]


def test_알림_정규화는_식별자만_지운다():
    assert normalize_alert_text("joinCode=V9KM 방에서 50건") == "joinCode=<code> 방에서 50건"
    assert normalize_message("id=6902 건수 50") == "id=<n> 건수 <n>"


def test_시간_대조_쌍은_같은_로그_내용이어도_다른_문제다():
    """타임스탬프만 다른 쌍. 시그니처가 시간을 안 보면 중복으로 잡혀 통째로 탈락한다."""
    tight = [f"[2026-08-26 14:1{i}:00] [ERROR] [,] --- [pool-1-thread-2] c.g.o.OutboxEventProcessor : 실패"
             for i in range(3)]
    spread = [f"[2026-08-26 0{i+1}:10:00] [ERROR] [,] --- [pool-1-thread-2] c.g.o.OutboxEventProcessor : 실패"
              for i in range(3)]
    a = scenario("a", "AppErrorLogSpike", "급증", "40건", tuple(tight))
    b = scenario("b", "AppErrorLogSpike", "급증", "40건", tuple(spread))
    assert signature(a) != signature(b)
    assert find_duplicates([a, b]) == []


def test_몇_초_차이는_같은_구간으로_본다():
    base = [f"[2026-08-26 14:10:0{i}] [ERROR] [,] --- [pool-1-thread-2] c.g.o.OutboxEventProcessor : 실패"
            for i in range(3)]
    shifted = [x.replace("14:10:", "14:11:") for x in base]
    a = scenario("a", "X", "s", "d", tuple(base))
    b = scenario("b", "X", "s", "d", tuple(shifted))
    assert signature(a) == signature(b)
