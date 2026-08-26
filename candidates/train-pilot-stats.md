## 합성 필터 통계

- 생성 시도: 20건, 생존: 16건 (80%)

| 검증기 | 탈락 건수 |
|---|---|
| slot-value | 3 |
| screen | 1 |

### 탈락 사유 상세

- `monitor-redis-stream-backlog-near-miss-918` [screen] 채점 기준은 주어진 로그 4건이 모두 '개별 메시지 처리 실패'를 보여준다고 서술했지만, 세 번째 로그는 'Redis Stream container 상태 확인 중 예외'를 보여주므로 '개별 메시지 처리 실패'에 해당하지 않습니다.
- `monitor-stream-backlog-nunchi-consumer-903` [slot-value] 로그 7: 이벤트 처리 실패 메시지 형식 위반: 이벤트 처리 실패: consumer=MiniGameStartConsumer, message=NunchiPressCommand 
- `monitor-stream-latency-compound-cause-910` [slot-value] 로그 0: 이벤트 처리 실패 메시지 형식 위반: 이벤트 처리 실패: consumer=RoomJoinConsumer(RoomJoinEvent), message=App Servi; 로그 1: 이벤트 처리 실패 메시지 형식 위반: 이벤트 처리 실패: consumer=RoomJoinConsumer(RoomJoinEvent), message=App Servi; 로그
- `monitor-stream-latency-partial-relevance-908` [slot-value] 로그 4: 이벤트 처리 실패 메시지 형식 위반: 이벤트 처리 실패: consumer=TapCommandEventConsumer, message=눈치게임 press 처리 지연으
