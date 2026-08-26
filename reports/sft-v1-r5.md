# 평가 리포트: sft-v1-r5

- 모델: gemini-2.5-flash
- 시나리오 33종, 시행 165건 (시행은 독립, 조기 중단 없음)
- 시행 PASS율: 90/165 (54.5%)
- 전 시행 PASS 시나리오: 18/33

| 시나리오 | PASS | acc 평균 | grd 평균 | 환각 | 오류 |
|---|---|---|---|---|---|
| monitor-5xx-compound-cause-32 | 0/5 | 0.0 | 0.0 | 0 | 0 |
| monitor-5xx-db-connection-failure | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-5xx-redis-connection-failure | 0/5 | 0.0 | 0.0 | 0 | 0 |
| monitor-alloy-down-observability-layer | 0/5 | 0.0 | 0.6 | 2 | 0 |
| monitor-app-error-log-spike-17 | 0/5 | 0.0 | 1.0 | 1 | 0 |
| monitor-app-error-log-spike-19 | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-circuit-breaker-open-02 | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-circuit-breaker-open-qr-uploads | 0/5 | 0.0 | 0.0 | 0 | 0 |
| monitor-db-pool-exhaustion-request-timeouts | 0/5 | 0.0 | 0.0 | 0 | 0 |
| monitor-db-pool-high-unrelated-game-errors | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-disk-high-unrelated-app-logs | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-disk-usage-high-unrelated-trap-08 | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-budget-burn-slow-11 | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-error-spike-cardgame-select-burst | 0/5 | 0.6 | 0.0 | 0 | 0 |
| monitor-error-spike-nunchi-consumer | 0/5 | 0.0 | 0.0 | 0 | 0 |
| monitor-error-spike-roomjoin-current-window | 0/5 | 2.0 | 5.0 | 0 | 0 |
| monitor-error-spike-sparse-two-lines | 0/5 | 0.0 | 0.0 | 0 | 0 |
| monitor-error-spike-stale-reingested-v2 | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-heap-high-sparse-unrelated-errors | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-http-5xx-ratio-high-sparse-logs | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-jvm-heap-high-unrelated-redis-errors-31 | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-login-drop-unrelated-logs | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-mass-ip-blocking-description-echo-trap | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-outbox-dead-letter-high-33 | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-outbox-deadletter-publish-failures | 0/5 | 2.0 | 5.0 | 0 | 0 |
| monitor-redis-stream-e2e-latency-27 | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-redis-stream-e2e-latency-35 | 0/5 | 0.0 | 0.0 | 0 | 0 |
| monitor-redis-stream-e2e-latency-high-05 | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-settlement-backlog-consumer-failures | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-stream-latency-container-recovery | 0/5 | 0.0 | 0.0 | 0 | 0 |
| monitor-target-down-mysql-exporter | 0/5 | 0.0 | 0.0 | 5 | 0 |
| monitor-ws-inbound-latency-sparse-evidence-18 | 5/5 | 5.0 | 5.0 | 0 | 0 |
| monitor-ws-probe-failed-edge-layer | 0/5 | 0.0 | 0.0 | 5 | 0 |
