from analysis.calibration import CalibrationReport, ProbeResult
from analysis.mutations import (
    BenignParaphrase,
    ComponentSwap,
    FabricatedCause,
    FlatAnswer,
    Probe,
    VerdictFlip,
    build_probes,
)

GROUNDED = "요약: DB 커넥션 풀이 포화됐습니다.\n근거 발견: 예\n원인 가설: 커넥션 누수\n제안 조치:\n- 풀 설정 점검"
UNGROUNDED = "요약: 근거를 찾지 못했습니다.\n근거 발견: 아니오\n원인 가설: (없음)\n제안 조치: (없음)"


def test_평탄화_답변을_되읽는다():
    flat = FlatAnswer.parse(GROUNDED)

    assert flat.evidence_found
    assert flat.summary == "DB 커넥션 풀이 포화됐습니다."
    assert flat.cause == "커넥션 누수"


def test_형식이_아닌_답변은_되읽지_못한다():
    assert FlatAnswer.parse("평가 실패") is None


def test_판정_뒤집기는_근거_발견만_바꾼다():
    flipped = VerdictFlip().apply(FlatAnswer.parse(GROUNDED)).render()

    assert "근거 발견: 아니오" in flipped
    assert "원인 가설: 커넥션 누수" in flipped


def test_원인_날조는_근거_없음_답변에만_적용된다():
    assert FabricatedCause().apply(FlatAnswer.parse(GROUNDED)) is None

    fabricated = FabricatedCause().apply(FlatAnswer.parse(UNGROUNDED)).render()
    assert "근거 발견: 아니오" in fabricated
    assert "원인 가설: (없음)" not in fabricated


def test_컴포넌트_바꿔치기는_근거_있음_답변에만_적용된다():
    assert ComponentSwap().apply(FlatAnswer.parse(UNGROUNDED)) is None

    swapped = ComponentSwap().apply(FlatAnswer.parse(GROUNDED)).render()
    assert "근거 발견: 예" in swapped
    assert "커넥션 누수" not in swapped


def test_무해한_말바꾸기는_판정과_원인을_보존한다():
    paraphrased = BenignParaphrase().apply(FlatAnswer.parse(GROUNDED)).render()

    assert "근거 발견: 예" in paraphrased
    assert "원인 가설: 커넥션 누수" in paraphrased
    assert paraphrased != GROUNDED


def test_프로브는_적용_가능한_변형만_만든다():
    grounded_probes = {p.mutation for p in build_probes("s", GROUNDED)}
    ungrounded_probes = {p.mutation for p in build_probes("s", UNGROUNDED)}

    assert "component-swap" in grounded_probes
    assert "fabricated-cause" not in grounded_probes
    assert "fabricated-cause" in ungrounded_probes
    assert "component-swap" not in ungrounded_probes
    assert "unmutated" in grounded_probes and "unmutated" in ungrounded_probes


def test_리포트는_놓친_오답과_과잉_탈락을_구분한다():
    results = [
        ProbeResult(Probe("a", "verdict-flip", "x", "FAIL"), "PASS", "놓침"),
        ProbeResult(Probe("b", "unmutated", "x", "PASS"), "FAIL", "과잉"),
        ProbeResult(Probe("c", "unmutated", "x", "PASS"), "PASS", "일치"),
    ]

    md = CalibrationReport().to_markdown("t", "m", results)

    assert "전체 일치율: 1/3" in md
    assert "놓친 오답(FAIL이어야 하는데 PASS): 1건" in md
    assert "과잉 탈락(PASS여야 하는데 FAIL): 1건" in md


def test_모호한_원인은_근거_있음_답변에만_적용된다():
    from analysis.mutations import VagueCause

    assert VagueCause().apply(FlatAnswer.parse(UNGROUNDED)) is None

    vague = VagueCause().apply(FlatAnswer.parse(GROUNDED)).render()
    assert "근거 발견: 예" in vague
    assert "커넥션 누수" not in vague


def test_확신을_흐려도_판정과_원인은_보존된다():
    from analysis.mutations import HedgedVerdict

    hedged = HedgedVerdict().apply(FlatAnswer.parse(GROUNDED)).render()

    assert "근거 발견: 예" in hedged
    assert "원인 가설: 커넥션 누수" in hedged
    assert "추가 확인이 필요할 수 있습니다" in hedged


def test_경계_프로브는_명백한_오답_프로브와_분리되어_있다():
    from analysis.mutations import GROSS_MUTATIONS, SUBTLE_MUTATIONS

    gross = {m.name for m in GROSS_MUTATIONS}
    subtle = {m.name for m in SUBTLE_MUTATIONS}

    assert gross & subtle == set()
    assert "verdict-flip" in gross
    assert "vague-cause" in subtle
