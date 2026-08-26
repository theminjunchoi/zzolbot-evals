# 평가 리포트: dev-mechanism-r2

- 모델: gemini-2.5-flash
- 시나리오 21종, 시행 42건 (시행은 독립, 조기 중단 없음)
- 시행 PASS율: 38/42 (90.5%)
- 전 시행 PASS 시나리오: 18/21

| 시나리오 | PASS | acc 평균 | grd 평균 | 환각 | 오류 |
|---|---|---|---|---|---|
| monitor-5xx-db-connection-failure | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-5xx-redis-connection-failure | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-alloy-down-observability-layer | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-circuit-breaker-open-qr-uploads | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-db-pool-exhaustion-request-timeouts | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-db-pool-high-unrelated-game-errors | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-disk-high-unrelated-app-logs | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-cardgame-select-burst | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-nunchi-consumer | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-roomjoin-current-window | 1/2 | 2.5 | 3.5 | 0 | 0 |
| monitor-error-spike-sparse-two-lines | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-stale-reingested-v2 | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-heap-high-sparse-unrelated-errors | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-login-drop-unrelated-logs | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-mass-ip-blocking-description-echo-trap | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-outbox-dead-letter-high-33 | 0/2 | 0.0 | 0.0 | 0 | 0 |
| monitor-outbox-deadletter-publish-failures | 1/2 | 4.0 | 4.0 | 0 | 0 |
| monitor-settlement-backlog-consumer-failures | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-stream-latency-container-recovery | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-target-down-mysql-exporter | 2/2 | 5.0 | 5.0 | 0 | 0 |
| monitor-ws-probe-failed-edge-layer | 2/2 | 5.0 | 5.0 | 0 | 0 |
