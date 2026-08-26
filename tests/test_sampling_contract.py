"""샘플링 파라미터 계약.

평가 경로는 결정적이어야 재현 가능하고, 합성 경로는 확률적이어야 다양한 시나리오가 나온다.
2026-08-26에 두 경로가 같은 클라이언트 기본값(temperature 0)을 공유해 복제 시나리오가
생산된 회귀를 막는다.
"""

import inspect

from harness.llm import GeminiJsonClient
from synthesis.cli import DEFAULT_TEMPERATURE, DEFAULT_TOP_P


def evaluation_defaults():
    params = inspect.signature(GeminiJsonClient.__init__).parameters
    return params["temperature"].default, params["top_p"].default


def test_평가_경로는_결정적이다():
    temperature, top_p = evaluation_defaults()

    assert temperature == 0.0
    assert top_p == 0.0


def test_합성_경로는_확률적이다():
    assert DEFAULT_TEMPERATURE > 0.5
    assert DEFAULT_TOP_P > 0.5


def test_두_경로의_샘플링이_분리되어_있다():
    eval_temperature, eval_top_p = evaluation_defaults()

    assert DEFAULT_TEMPERATURE != eval_temperature
    assert DEFAULT_TOP_P != eval_top_p
