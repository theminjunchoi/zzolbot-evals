# 평가 리포트: python-baseline-r3-2026-08-26

- 모델: gemini-2.5-flash
- 시나리오 20종, 시행 60건 (시행은 독립, 조기 중단 없음)
- 시행 PASS율: 60/60 (100.0%)
- 전 시행 PASS 시나리오: 20/20

| 시나리오 | PASS | acc 평균 | grd 평균 | 환각 | 오류 |
|---|---|---|---|---|---|
| monitor-5xx-db-connection-failure | 3/3 | 5.0 | 5.0 | 1 | 0 |
| monitor-5xx-redis-connection-failure | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-alloy-down-observability-layer | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-circuit-breaker-open-qr-uploads | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-db-pool-exhaustion-request-timeouts | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-db-pool-high-unrelated-game-errors | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-disk-high-unrelated-app-logs | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-cardgame-select-burst | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-nunchi-consumer | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-roomjoin-current-window | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-sparse-two-lines | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-stale-reingested-v2 | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-heap-high-sparse-unrelated-errors | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-login-drop-unrelated-logs | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-mass-ip-blocking-description-echo-trap | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-outbox-deadletter-publish-failures | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-settlement-backlog-consumer-failures | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-stream-latency-container-recovery | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-target-down-mysql-exporter | 3/3 | 5.0 | 5.0 | 0 | 0 |
| monitor-ws-probe-failed-edge-layer | 3/3 | 5.0 | 5.0 | 0 | 0 |
