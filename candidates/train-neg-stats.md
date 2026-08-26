## 합성 필터 통계

- 생성 시도: 44건, 생존: 41건 (93%)

| 검증기 | 탈락 건수 |
|---|---|
| screen | 3 |

### 탈락 사유 상세

- `monitor-redis-backlog-minigame-room-join-near-miss-2024` [screen] 채점 기준은 적체가 보고된 스트림이 'minigame'이라고 서술했으나, 알림에는 'minigame' 스트림에 대한 언급이 없고 'prod-app'만 언급되어 있습니다.
- `monitor-redis-backlog-room-join-other-streams-near-miss-2017` [screen] 채점 기준은 적체가 보고된 스트림이 'room:join'이라고 서술했으나, 알림과 로그 어디에도 'room:join'이라는 스트림명은 언급되어 있지 않습니다.
- `monitor-redis-backlog-settlement-laddergame-near-miss-2022` [screen] 채점 기준에서 적체가 보고된 스트림이 'settlement:result'라고 서술했으나, 실제 알림과 로그 어디에도 'settlement:result'라는 스트림명은 등장하지 않습니다.
