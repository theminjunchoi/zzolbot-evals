# judge 캘리브레이션: judge-calibration-v1

- judge 모델: gemini-2.5-flash
- 프로브 40건 (참조 라벨은 변형 방식이 결정한다)
- 전체 일치율: 40/40 (100.0%)
- 놓친 오답(FAIL이어야 하는데 PASS): 0건
- 과잉 탈락(PASS여야 하는데 FAIL): 0건

| 변형 | 참조 라벨 | 일치 | 일치율 |
|---|---|---|---|
| benign-paraphrase | PASS | 10/10 | 100% |
| component-swap | FAIL | 5/5 | 100% |
| fabricated-cause | FAIL | 5/5 | 100% |
| unmutated | PASS | 10/10 | 100% |
| verdict-flip | FAIL | 10/10 | 100% |
