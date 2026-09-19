# 보상 측정: 31-parity-llamacpp

- 시나리오 33종 (근거 있음 15 / 없음 18)
- 엔진 llamacpp, 모델 merged=training/gguf/sft-v6-s1-bf16.gguf, 프롬프트 production, judge 미사용
- 배점 schema 0.1 / verdict 0.5 / citation 0.4 / specificity 0.0
- best-of-n: n=1, temperature=0.8
- 인용 제약 디코딩: 없음

| 팔 | 그리디 평균 | 최고 평균 | 상한 여유 | 인용 통과 | 오탐 | 파싱 실패 |
|---|---|---|---|---|---|---|
| merged | 0.885 | 0.885 | **+0.000** | 12/15 | 5/18 | 0 |
