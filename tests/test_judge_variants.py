"""judge 변형 계약. production은 팀 레포와 같아야 하고, 실험 변형은 규칙을 덧붙이기만 한다."""

from harness.judge import JUDGE_VARIANTS, SPECIFICITY_RULE, SYSTEM_INSTRUCTION


def test_production_변형은_운영_프롬프트_그대로다():
    assert JUDGE_VARIANTS["production"] == SYSTEM_INSTRUCTION


def test_실험_변형은_기존_스키마_지시를_보존한다():
    variant = JUDGE_VARIANTS["specificity-aware"]

    assert '"accuracy": 0~5 정수' in variant
    assert "설명 텍스트 없이 JSON 객체 하나만 출력하라." in variant


def test_실험_변형은_구체성_기준을_덧붙인다():
    variant = JUDGE_VARIANTS["specificity-aware"]

    assert SPECIFICITY_RULE.strip() in variant
    assert "accuracy는 3 이하이고 verdict는 FAIL" in variant


def test_실험_변형은_과잉_엄격_가드를_포함한다():
    variant = JUDGE_VARIANTS["specificity-aware"]

    assert "채점 기준이 요구하지 않은 요소는 채점 대상이 아니다" in variant
