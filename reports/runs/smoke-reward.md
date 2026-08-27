# 보상 측정: smoke

- 시나리오 2종 (근거 있음 2 / 없음 0)
- 모델 mlx-community/Qwen2.5-1.5B-Instruct-4bit, 프롬프트 production, judge 미사용
- 배점 schema 0.1 / verdict 0.5 / citation 0.4 / specificity 0.0
- best-of-n: n=2, temperature=0.8

| 팔 | 그리디 평균 | 최고 평균 | 상한 여유 | 인용 통과 | 오탐 | 파싱 실패 |
|---|---|---|---|---|---|---|
| v4 | 0.800 | 1.000 | **+0.200** | 1/2 | 0/0 | 0 |
