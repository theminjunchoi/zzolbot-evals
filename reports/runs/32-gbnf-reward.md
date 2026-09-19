# 보상 측정: 32-gbnf

- 시나리오 33종 (근거 있음 15 / 없음 18)
- 엔진 llamacpp, 모델 q8_0=training/gguf/sft-v6-s1-q8_0.gguf, q4_k_m=training/gguf/sft-v6-s1-q4_k_m.gguf, 프롬프트 production, judge 미사용
- 배점 schema 0.1 / verdict 0.5 / citation 0.4 / specificity 0.0
- best-of-n: n=1, temperature=0.8
- 인용 제약 디코딩: 적용

| 팔 | 그리디 평균 | 최고 평균 | 상한 여유 | 인용 통과 | 오탐 | 파싱 실패 |
|---|---|---|---|---|---|---|
| q8_0 | 0.909 | 0.909 | **+0.000** | 14/15 | 5/18 | 0 |
| q4_k_m | 0.924 | 0.924 | **+0.000** | 12/15 | 2/18 | 0 |
