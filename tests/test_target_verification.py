"""학습 정답 검증 계약. 정답이 틀리면 틀린 것을 가르치므로 기계적으로 막는다."""

from harness.domain import Alert, Analysis, Scenario
from training.verification import verify_target

LOG_A = "[2026-08-25 10:00:00.000] [ERROR] [,] --- [pool-11-thread-1] c.global.outbox.OutboxEventProcessor : Outbox 이벤트 최대 재시도 초과, DEAD_LETTER 전환: id=8241, streamKey=laddergame"
LOG_B = "[2026-08-25 10:01:00.000] [ERROR] [,] --- [pool-11-thread-1] c.global.outbox.OutboxEventProcessor : Outbox 이벤트 최대 재시도 초과, DEAD_LETTER 전환: id=8242, streamKey=laddergame"


def scenario(rubric: str) -> Scenario:
    return Scenario(
        name="monitor-x", question="q", rubric=rubric, source="MANUAL",
        alert=Alert("OutboxDeadLetterHigh", "warning", "fp",
                    "Outbox DEAD_LETTER 적체 (> 10, prod-app)",
                    "재시도 초과로 DEAD_LETTER 전환된 outbox 이벤트가 14건.", {"job": "prod-app"}),
        log_samples=(LOG_A, LOG_B), log_environment="prod")


YES_RUBRIC = "'근거 발견: 예'로 판정하고 laddergame 발행 실패를 원인으로 제시하면 정답. 아니면 오답."
NO_RUBRIC = "'근거 발견: 아니오'로 판정하고 원인 가설을 내지 않아야 정답. 아니면 오답."


def flat(reasons: dict) -> list[str]:
    return [r for rs in reasons.values() for r in rs]


def test_올바른_정답은_모든_검사를_통과한다():
    target = Analysis("laddergame 스트림 발행이 반복 실패했습니다.", "laddergame 스트림 발행 경로 장애",
                      ("점검",), True, LOG_A)

    assert flat(verify_target(scenario(YES_RUBRIC), target)) == []


def test_인용문이_로그에_없으면_탈락한다():
    target = Analysis("요약", "원인", ("조치",), True, "[2026-08-25 10:00:00.000] [ERROR] 지어낸 로그")

    assert any("인용문이 로그에 없음" in r for r in flat(verify_target(scenario(YES_RUBRIC), target)))


def test_로그_일부만_인용하면_탈락한다():
    target = Analysis("요약", "원인", ("조치",), True, "2026-08-25 10:00:00.000")

    assert any("한 줄 전체가 아닌" in r for r in flat(verify_target(scenario(YES_RUBRIC), target)))


def test_기대_판정과_다른_정답은_탈락한다():
    target = Analysis("요약", "", (), False, "")

    assert any("기대 판정 예인데" in r for r in flat(verify_target(scenario(YES_RUBRIC), target)))


def test_근거가_없는데_원인을_말하면_탈락한다():
    target = Analysis("근거를 찾지 못했습니다.", "Redis 지연으로 보입니다", (), False, "")

    assert any("근거 없음인데 원인 가설이 있음" in r for r in flat(verify_target(scenario(NO_RUBRIC), target)))


def test_지어낸_식별자가_섞이면_탈락한다():
    target = Analysis("cardgame:select 스트림에서 문제가 발생했습니다.",
                      "MiniGameStartConsumer 처리 실패", ("조치",), True, LOG_A)

    reasons = flat(verify_target(scenario(YES_RUBRIC), target))
    assert any("MiniGameStartConsumer" in r for r in reasons)


def test_로그에_있는_식별자는_통과한다():
    target = Analysis("OutboxEventProcessor가 laddergame 발행에 반복 실패했습니다.",
                      "laddergame 스트림 발행 경로 장애", ("조치",), True, LOG_A)

    assert flat(verify_target(scenario(YES_RUBRIC), target)) == []


def test_부분_인용은_로그_한_줄_전체로_복원된다():
    from training.dataset import repair_citation

    target = Analysis("요약", "원인", ("조치",), True, "id=8241, streamKey=laddergame")

    repaired = repair_citation(target, scenario(YES_RUBRIC))

    assert repaired.evidence_line == LOG_A
    assert flat(verify_target(scenario(YES_RUBRIC), repaired)) == []


def test_여러_줄에_걸치는_인용은_복원하지_않는다():
    from training.dataset import repair_citation

    target = Analysis("요약", "원인", ("조치",), True, "Outbox 이벤트 최대 재시도 초과")

    repaired = repair_citation(target, scenario(YES_RUBRIC))

    assert repaired.evidence_line == "Outbox 이벤트 최대 재시도 초과"
    assert flat(verify_target(scenario(YES_RUBRIC), repaired)) != []


def test_학습_샘플은_대화_형식으로_직렬화된다():
    from training.dataset import build_sample

    target = Analysis("요약문", "원인문", ("조치",), True, LOG_A)
    sample = build_sample(scenario(YES_RUBRIC), target)
    chat = sample.to_chat()

    assert [m["role"] for m in chat["messages"]] == ["system", "user", "assistant"]
    assert '"evidenceFound": true' in chat["messages"][2]["content"]
    assert LOG_A in chat["messages"][2]["content"]


def test_내용이_같은_시나리오는_이름이_달라도_중복이다():
    from harness.similarity import find_duplicates, signature

    # 시각을 통째로 옮기고 id만 바꾼다. 시간 **간격**은 그대로여야 같은 문제다.
    # 한 줄만 옮기면 몰린 것이 흩어진 것으로 바뀌어 다른 문제가 된다(의도된 동작).
    a = scenario(YES_RUBRIC)
    b = Scenario(name="monitor-y", question=a.question, rubric=a.rubric, source=a.source,
                 alert=a.alert,
                 log_samples=tuple(l.replace("8241", "9999").replace("8242", "9998")
                                    .replace("2026-08-25 10:0", "2026-08-27 14:3")
                                   for l in a.log_samples),
                 log_environment=a.log_environment)

    assert signature(a) == signature(b)
    assert find_duplicates([b], against=[a]) == [("monitor-y", "monitor-x")]


def test_로그_구성이_다르면_중복이_아니다():
    from harness.similarity import find_duplicates

    a = scenario(YES_RUBRIC)
    b = Scenario(name="monitor-z", question=a.question, rubric=a.rubric, source=a.source,
                 alert=a.alert, log_samples=a.log_samples[:1], log_environment=a.log_environment)

    assert find_duplicates([b], against=[a]) == []


def test_오답_조건_절의_문구를_기대_판정으로_읽지_않는다():
    from training.verification import expects_evidence

    tricky = ("'근거 발견: 아니오'로 판정하고 원인 가설을 내지 않아야 정답. "
              "'근거 발견: 예'로 판정하면 오답.")

    assert not expects_evidence(scenario(tricky))


def test_명시된_expected_필드를_우선한다():
    from training.verification import expects_evidence

    base = scenario("'근거 발견: 예'로 판정하면 정답. 아니면 오답.")
    overridden = Scenario(**{**base.__dict__, "expected": "아니오"})

    assert expects_evidence(base)
    assert not expects_evidence(overridden)
