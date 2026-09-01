# 보상 측정: adp-mlx

- 시나리오 33종 (근거 있음 15 / 없음 18)
- 엔진 mlx, 모델 Qwen/Qwen2.5-1.5B-Instruct, 프롬프트 production, judge 미사용
- 배점 schema 0.1 / verdict 0.5 / citation 0.4 / specificity 0.0
- best-of-n: n=1, temperature=0.8
- 인용 제약 디코딩: 없음

| 팔 | 그리디 평균 | 최고 평균 | 상한 여유 | 인용 통과 | 오탐 | 파싱 실패 |
|---|---|---|---|---|---|---|
| v6 | 0.903 | 0.903 | **+0.000** | 13/15 | 4/18 | 0 |
