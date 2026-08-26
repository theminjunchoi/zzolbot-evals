# judge 캘리브레이션: judge-cal-v3-specificity

- judge 모델: gemini-2.5-flash
- 프로브 65건 (참조 라벨은 변형 방식이 결정한다)
- 전체 일치율: 64/65 (98.5%)
- 놓친 오답(FAIL이어야 하는데 PASS): 0건
- 과잉 탈락(PASS여야 하는데 FAIL): 1건

| 변형 | 참조 라벨 | 일치 | 일치율 |
|---|---|---|---|
| benign-paraphrase | PASS | 10/10 | 100% |
| component-swap | FAIL | 5/5 | 100% |
| fabricated-cause | FAIL | 5/5 | 100% |
| hedged-summary | PASS | 10/10 | 100% |
| no-actions | PASS | 9/10 | 90% |
| unmutated | PASS | 10/10 | 100% |
| vague-cause | FAIL | 5/5 | 100% |
| verdict-flip | FAIL | 10/10 | 100% |

## 과잉 탈락

- `monitor-app-error-log-spike-17` [no-actions] 봇은 알림의 근거를 찾지 못했다고 올바르게 판정했으나, 채점 기준이 요구하는 '표본 부족'을 명시적으로 언급하지 않아 감점 처리됩니다.
