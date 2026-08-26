# 확정 골든셋 20종 자바 하네스 측정 (v3)

- 일시: 2026-08-26 (run id 1, label `golden-v3-final-20`)
- 대상: 개인 골든셋 확정 20종만 적재 (worktree 기존 시드 5종은 측정 전 임시 제거, 측정 후 git으로 원복)
- 환경: worktree feat/1626 (HEAD bdb3b40f), local 프로파일, 라이브 gemini-2.5-flash (분석기와 judge 동일 모델, temperature 0)
- 실행: repeats=1, kind=monitor
- 주의: 단일 실행이라 통계적 의미는 제한적. 공식 baseline은 Python 하네스에서 반복 실행으로 재측정 예정.

## 결과: 18/20 PASS

| 시나리오 | 기대 | 판정 | acc | grd | hall |
|---|---|---|---|---|---|
| monitor-db-pool-exhaustion-request-timeouts | 예 | PASS | 5 | 5 | F |
| monitor-db-pool-high-unrelated-game-errors | 아니오 | PASS | 5 | 5 | F |
| monitor-settlement-backlog-consumer-failures | 예 | PASS | 5 | 5 | F |
| monitor-stream-latency-container-recovery | 예 | PASS | 5 | 5 | F |
| monitor-heap-high-sparse-unrelated-errors | 아니오 | PASS | 5 | 5 | F |
| monitor-5xx-redis-connection-failure | 예 | PASS | 5 | 5 | F |
| monitor-outbox-deadletter-publish-failures | 예 | PASS | 3 | 5 | F |
| monitor-ws-probe-failed-edge-layer | 아니오 | PASS | 5 | 5 | F |
| monitor-error-spike-nunchi-consumer | 예 | PASS | 5 | 5 | F |
| monitor-mass-ip-blocking-description-echo-trap | 아니오 | PASS | 5 | 5 | F |
| monitor-error-spike-stale-reingested-v2 | 아니오 | **FAIL** | 0 | 0 | F |
| monitor-error-spike-roomjoin-current-window | 예 | PASS | 5 | 5 | F |
| monitor-error-spike-sparse-two-lines | 아니오 | **FAIL** | 0 | 0 | T |
| monitor-error-spike-cardgame-select-burst | 예 | PASS | 5 | 5 | F |
| monitor-circuit-breaker-open-qr-uploads | 예 | PASS | 5 | 5 | F |
| monitor-login-drop-unrelated-logs | 아니오 | PASS | 5 | 5 | F |
| monitor-alloy-down-observability-layer | 아니오 | PASS | 5 | 5 | F |
| monitor-target-down-mysql-exporter | 아니오 | PASS | 5 | 5 | F |
| monitor-5xx-db-connection-failure | 예 | PASS | 5 | 5 | F |
| monitor-disk-high-unrelated-app-logs | 아니오 | PASS | 5 | 5 | F |

- 예 케이스: 10/10 PASS (원인 판별 쌍 6 vs 19도 각각 Redis/DB로 정확히 구분)
- 아니오 케이스: 8/10 PASS
- 대조군 쌍 4개 중 3개(1↔2, 6↔19, 10↔14)는 양쪽 모두 정답, 11↔12는 12(정합 시각)만 정답

## 오답노트

FAIL 2건이 이전 리허설과 동일한 축에서 재현됐다. 버린 기존 시드가 아니라 새로 작성한 시나리오에서도 같은 실패가 나왔으므로 **약점이 체계적임이 확정**됐다.

1. **시간적 접지 실패 (stale-reingested-v2)**: 로그 본문 타임스탬프가 전날에 흩어져 있는데(재적재 아티팩트) 이를 지적하지 못하고 '근거 발견: 예' + "방 참가 및 이벤트 처리 오류" 가설을 냈다. 대조군 12번(같은 내용, 정합 시각)은 정확히 맞혔으므로, 봇은 내용 관련성만 보고 시각 정합성은 전혀 보지 않는다는 게 입증된다.
2. **양적 접지 실패 (sparse-two-lines)**: 25분 떨어진 2줄로 38건/5분 스파이크를 설명할 수 없는데 '근거 발견: 예' + Oracle Storage 오류를 원인으로 단정했다(judge가 hallucination=true 판정).

### 패턴 해석

- 주제적 접지(로그가 알림과 topically 관련되는가)는 코드 검증(citedInLogs) + 프롬프트 규칙으로 강제되어 **10/10 전부 통과**. 무관 로그 함정, 레이어 혼동, description 가설 주입까지 다 막았다.
- 시간적 접지(타임스탬프가 알림 시각과 정합하는가)와 양적 접지(로그 건수가 알림 수치를 설명하는가)는 프롬프트에도 코드에도 없어서 **이 축만 골라서 실패**한다.

### 다음 실험 (개선 전후 비교 대상)

1. 프롬프트에 시간 정합성 규칙 추가: "로그 타임스탬프가 알림 발화 시각과 동떨어져 있으면 근거로 삼지 마라"
2. 양적 규칙 추가: "알림의 건수를 설명하기에 로그 표본이 현저히 부족하면 근거 불충분으로 판정하라"
3. 또는 코드 레벨: 조회 창 밖 타임스탬프 로그를 입력 단계에서 태깅
4. 개선 후 이 20종 재측정 → 11, 13 PASS 전환 + 나머지 18종 무회귀 확인이 성공 기준

## 파일

- 원본: `runs/2026-08-26-final20-run-raw.json`, `runs/2026-08-26-final20-scenarios-raw.json`
- 시드: `../golden-set/monitor/` 확정 20종
- 이전 리허설(v2, 15종 혼합): `01-자바-하네스-리허설.md`
