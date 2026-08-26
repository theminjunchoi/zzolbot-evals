# 평가 리포트: gemini-graph-strict-r1

- 모델: gemini-2.5-flash
- 시나리오 33종, 시행 33건 (시행은 독립, 조기 중단 없음)
- 시행 PASS율: 27/33 (81.8%)
- 전 시행 PASS 시나리오: 27/33

| 시나리오 | PASS | acc 평균 | grd 평균 | 환각 | 오류 |
|---|---|---|---|---|---|
| monitor-5xx-compound-cause-32 | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-5xx-db-connection-failure | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-5xx-redis-connection-failure | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-alloy-down-observability-layer | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-app-error-log-spike-17 | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-app-error-log-spike-19 | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-circuit-breaker-open-02 | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-circuit-breaker-open-qr-uploads | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-db-pool-exhaustion-request-timeouts | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-db-pool-high-unrelated-game-errors | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-disk-high-unrelated-app-logs | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-disk-usage-high-unrelated-trap-08 | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-budget-burn-slow-11 | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-cardgame-select-burst | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-nunchi-consumer | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-roomjoin-current-window | 0/1 | 3.0 | 5.0 | 0 | 0 |
| monitor-error-spike-sparse-two-lines | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-stale-reingested-v2 | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-heap-high-sparse-unrelated-errors | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-http-5xx-ratio-high-sparse-logs | 0/1 | 0.0 | 2.0 | 0 | 0 |
| monitor-jvm-heap-high-unrelated-redis-errors-31 | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-login-drop-unrelated-logs | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-mass-ip-blocking-description-echo-trap | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-outbox-dead-letter-high-33 | 0/1 | 0.0 | 2.0 | 0 | 0 |
| monitor-outbox-deadletter-publish-failures | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-redis-stream-e2e-latency-27 | 0/1 | 3.0 | 4.0 | 0 | 0 |
| monitor-redis-stream-e2e-latency-35 | 0/1 | 1.0 | 5.0 | 0 | 0 |
| monitor-redis-stream-e2e-latency-high-05 | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-settlement-backlog-consumer-failures | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-stream-latency-container-recovery | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-target-down-mysql-exporter | 1/1 | 5.0 | 5.0 | 0 | 0 |
| monitor-ws-inbound-latency-sparse-evidence-18 | 0/1 | 0.0 | 1.0 | 0 | 0 |
| monitor-ws-probe-failed-edge-layer | 1/1 | 5.0 | 5.0 | 0 | 0 |
