"""LLM 전송 계층. 프롬프트 내용은 모르고 호출, 레이트리밋, 재시도만 담당한다."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod


class LlmJsonClient(ABC):
    """system instruction과 user prompt를 받아 JSON 문자열을 돌려주는 포트."""

    @abstractmethod
    def generate_json(self, system_instruction: str, prompt: str) -> str: ...


class GeminiJsonClient(LlmJsonClient):
    """자바 봇과 동일 조건의 Gemini 호출: temperature 0, topP 0, JSON 강제.

    무료 티어 분당 한도를 존중하기 위해 호출 간 최소 간격을 둔다 (기본 6.5초 = 약 9회/분).
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash",
                 min_interval_s: float = 6.5, max_attempts: int = 3):
        from google import genai  # 지연 import: 테스트가 SDK 없이도 다른 모듈을 쓸 수 있게

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._min_interval_s = min_interval_s
        self._max_attempts = max_attempts
        self._last_call_at = 0.0

    def generate_json(self, system_instruction: str, prompt: str) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,
            top_p=0.0,
            response_mime_type="application/json",
        )
        last_error: Exception | None = None
        for attempt in range(self._max_attempts):
            self._respect_rate_limit()
            try:
                response = self._client.models.generate_content(
                    model=self._model, contents=prompt, config=config)
                return response.text
            except Exception as e:  # noqa: BLE001 - 재시도 대상은 전송 오류 전반
                last_error = e
                time.sleep(2.0 * (2 ** attempt))
        raise RuntimeError(f"Gemini 호출 {self._max_attempts}회 실패: {last_error}") from last_error

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_call_at
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_call_at = time.monotonic()
