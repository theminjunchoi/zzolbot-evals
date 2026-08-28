# 보상 측정: dpo-v1c

- 시나리오 33종 (근거 있음 15 / 없음 18)
- 모델 mlx-community/Qwen2.5-1.5B-Instruct-4bit, 프롬프트 production, judge 미사용
- 배점 schema 0.1 / verdict 0.5 / citation 0.4 / specificity 0.0
- best-of-n: n=1, temperature=0.8
- 인용 제약 디코딩: 적용

| 팔 | 그리디 평균 | 최고 평균 | 상한 여유 | 인용 통과 | 오탐 | 파싱 실패 |
|---|---|---|---|---|---|---|
| dpoc | 0.833 | 0.833 | **+0.000** | 15/15 | 11/18 | 0 |
