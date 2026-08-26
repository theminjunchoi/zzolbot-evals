# judge 캘리브레이션: judge-calibration-v2-subtle

- judge 모델: gemini-2.5-flash
- 프로브 25건 (참조 라벨은 변형 방식이 결정한다)
- 전체 일치율: 22/25 (88.0%)
- 놓친 오답(FAIL이어야 하는데 PASS): 3건
- 과잉 탈락(PASS여야 하는데 FAIL): 0건

| 변형 | 참조 라벨 | 일치 | 일치율 |
|---|---|---|---|
| hedged-summary | PASS | 10/10 | 100% |
| no-actions | PASS | 10/10 | 100% |
| vague-cause | FAIL | 2/5 | 40% |

## 놓친 오답

- `monitor-5xx-db-connection-failure` [vague-cause] 봇은 주어진 로그를 바탕으로 근거를 정확히 발견하고, 요약에서 데이터베이스 연결 문제를 근본 원인 가설로 제시하여 채점 기준을 충족했다. 다만, '원인 가설' 항목 자체는 다소 일반적이었다.
- `monitor-5xx-redis-connection-failure` [vague-cause] 봇은 주어진 로그를 바탕으로 Redis 연결 실패를 5xx의 원인으로 정확히 지목하고 근거 발견 여부도 올바르게 판단했습니다. 다만, '원인 가설' 필드에 구체적인 원인 대신 일반적인 문구를 사용한 점은 아쉽습니다.
- `monitor-circuit-breaker-open-02` [vague-cause] 봇은 근거 발견을 정확히 판정했으며, 제안 조치를 통해 근본 원인(Oracle Object Storage 서비스 장애 또는 네트워크 단절)을 올바르게 제시했으나, 원인 가설이 다소 포괄적입니다.
