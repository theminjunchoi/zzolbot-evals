"""대조 쌍 무결성 검사를 고정한다.

로그가 바이트 단위로 같지 않으면 대조 쌍이 아니다. 이 검사가 없으면 생성기가 로그를
미묘하게 바꿔도 통과해, 대조 학습의 전제가 조용히 무너진다.
"""

from __future__ import annotations

from synthesis.pairing import check_pairs, pair_key, paired_names

LINES = ["[2026-08-26 14:10:05.123] [ERROR] [,] --- [pool-1-thread-2] c.g.o.OutboxEventProcessor : 실패"]


def side(base: str, s: str, expected: str, summary: str, lines=None) -> dict:
    return {
        "name": f"{base}-{s}",
        "expected": expected,
        "logEnvironment": "prod",
        "logSamples": list(lines if lines is not None else LINES),
        "alert": {"alertname": "A", "summary": summary, "description": f"{summary} 상세"},
    }


def good_pair(base="monitor-x-pair01"):
    return [side(base, "a", "예", "Outbox 적체"), side(base, "b", "아니오", "디스크 사용률 높음")]


def test_이름에서_쌍을_식별한다():
    assert pair_key("monitor-x-pair01-a") == ("monitor-x-pair01", "a")
    assert pair_key("monitor-x-single") is None


def test_온전한_쌍은_문제가_없다():
    assert check_pairs(good_pair()) == []
    assert paired_names(good_pair()) == {"monitor-x-pair01-a", "monitor-x-pair01-b"}


def test_로그가_한_글자라도_다르면_탈락():
    a, b = good_pair()
    b["logSamples"] = [LINES[0].replace("14:10:05.123", "14:10:05.124")]
    problems = check_pairs([a, b])
    assert len(problems) == 1
    assert "로그가 서로 다르다" in problems[0].reason
    assert paired_names([a, b]) == set()


def test_기대_판정이_같으면_대조가_아니다():
    a, b = good_pair()
    b["expected"] = "예"
    assert any("기대 판정이 같다" in p.reason for p in check_pairs([a, b]))


def test_알림_본문이_같으면_바뀐_것이_없다():
    a, b = good_pair()
    b["alert"] = dict(a["alert"])
    b["expected"] = "아니오"
    assert any("알림 본문이 같다" in p.reason for p in check_pairs([a, b]))


def test_짝이_없으면_탈락():
    a, _ = good_pair()
    problems = check_pairs([a])
    assert len(problems) == 1
    assert "짝이 없다" in problems[0].reason


def test_로그_환경이_다르면_변수가_섞인_것이다():
    a, b = good_pair()
    b["logEnvironment"] = "dev"
    assert any("로그 환경이 다르다" in p.reason for p in check_pairs([a, b]))


def test_쌍이_아닌_시나리오는_그냥_지나간다():
    assert check_pairs([{"name": "monitor-혼자", "logSamples": LINES}]) == []


def test_여러_쌍_중_문제_있는_것만_제외한다():
    ok = good_pair("monitor-ok-pair")
    bad = good_pair("monitor-bad-pair")
    bad[1]["logSamples"] = ["다른 줄"]
    names = paired_names(ok + bad)
    assert names == {"monitor-ok-pair-a", "monitor-ok-pair-b"}


# --- 시간 대조 쌍 ---

from synthesis.pairing import check_temporal_pairs, log_skeleton, span_minutes

TIGHT = [f"[2026-08-26 14:1{i}:0{i}] [ERROR] [,] --- [pool-1-thread-2] c.g.o.OutboxEventProcessor : 실패"
         for i in range(3)]
SPREAD = [f"[2026-08-26 0{i+1}:10:05] [ERROR] [,] --- [pool-1-thread-2] c.g.o.OutboxEventProcessor : 실패"
          for i in range(3)]


def temporal(base="monitor-x-tp01"):
    a = side(base, "a", "예", "급증", TIGHT)
    b = side(base, "b", "아니오", "급증", SPREAD)
    return [a, b]


def test_타임스탬프를_떼면_같은_뼈대다():
    assert log_skeleton(TIGHT[0]) == log_skeleton(SPREAD[0])


def test_시간창을_분으로_잰다():
    assert span_minutes(TIGHT) < 5
    assert span_minutes(SPREAD) > 60


def test_온전한_시간_대조_쌍은_통과한다():
    assert check_temporal_pairs(temporal()) == []


def test_줄_수가_다르면_탈락():
    a, b = temporal(); b["logSamples"] = SPREAD[:2]
    assert any("줄 수가 다르다" in p.reason for p in check_temporal_pairs([a, b]))


def test_타임스탬프_외의_내용이_다르면_탈락():
    a, b = temporal()
    b["logSamples"] = [x.replace("OutboxEventProcessor", "EventDispatcher") for x in SPREAD]
    assert any("타임스탬프 외의 내용이 다르다" in p.reason for p in check_temporal_pairs([a, b]))


def test_예쪽이_퍼져_있으면_탈락():
    a, b = temporal(); a["logSamples"] = SPREAD; b["logSamples"] = SPREAD
    assert any("분에 퍼져 있다" in p.reason for p in check_temporal_pairs([a, b]))


def test_아니오쪽이_몰려_있으면_탈락():
    a, b = temporal(); b["logSamples"] = TIGHT
    assert any("분뿐이다" in p.reason for p in check_temporal_pairs([a, b]))
