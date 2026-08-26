"""프롬프트 변형 계약.

production 변형은 팀 레포 운영 프롬프트와 같아야 비교가 성립한다. 실험 변형은 규칙을
덧붙이기만 하고 기존 규칙을 지우지 않는다.
"""

from harness.analyzer import MECHANISM_RULE, PROMPT_VARIANTS, SYSTEM_INSTRUCTION


def test_production_변형은_운영_프롬프트_그대로다():
    assert PROMPT_VARIANTS["production"] == SYSTEM_INSTRUCTION


def test_실험_변형은_기존_규칙을_보존한다():
    variant = PROMPT_VARIANTS["mechanism-aware"]

    assert "시간 정합성:" in variant
    assert "양적 정합성:" in variant
    assert "설명 텍스트 없이 JSON 객체 하나만 출력하라." in variant


def test_실험_변형은_규칙을_덧붙인다():
    variant = PROMPT_VARIANTS["mechanism-aware"]

    assert "컴포넌트 정합성:" in variant
    assert MECHANISM_RULE.strip() in variant
    assert len(variant) > len(SYSTEM_INSTRUCTION)


def test_덧붙인_규칙은_출력_지시_앞에_온다():
    variant = PROMPT_VARIANTS["mechanism-aware"]

    assert variant.index("컴포넌트 정합성:") < variant.index("없는 수치")
