# 학습 데이터 빌드: sft-tpair

- 교사 모델: gemini-2.5-flash
- 시나리오 36건 중 채택 32건 (89%)
- train 28 / valid 4

| 탈락 사유 | 건수 |
|---|---|
| verdict | 4 |

### 탈락 상세

- `monitor-jdbc-connection-5xx-tpb05-b` [verdict] 기대 판정 아니오인데 정답은 예
- `monitor-player-disconnected-consumer-burst-tpa03-a` [verdict] 기대 판정 예인데 정답은 아니오
- `monitor-room-join-async-failure-burst-tpa09-a` [verdict] 기대 판정 예인데 정답은 아니오
- `monitor-room-join-ws-failures-tpb03-a` [verdict] 기대 판정 예인데 정답은 아니오
