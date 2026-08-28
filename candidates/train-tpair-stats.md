## 합성 필터 통계

- 생성 시도: 40건, 생존: 38건 (95%)

| 검증기 | 탈락 건수 |
|---|---|
| screen | 2 |

### 탈락 사유 상세

- `monitor-cardgame-select-disconnect-tpb08-a` [screen] 채점 기준은 로그가 'WS 연결 실패 급증의 직접 근거'이며 'WS 세션이 끊기며' 발생한 것이 원인이라고 서술하지만, 실제 로그에는 'WS', 'WebSocket', 'STOMP', '연결 실패', '세션 끊김' 등 WebSocket 연결 실패나 세션 단절을 직접적으로 가리키는 문자열이 전혀 없습니다. 로그는 단지 '이벤트 처리 실패'만을 보여줍니다.
- `monitor-nunchi-press-errors-tpb06-a` [screen] 채점 기준은 주어진 ERROR 로그 7줄이 모두 '눈치게임 press 커맨드 소비 오류' 또는 'nunchi 게임 스케줄 실행 예외'에 해당한다고 서술했으나, 5번째 로그는 'Unexpected error occurred in scheduled task'로 'nunchi'라는 컴포넌트명이 명시되어 있지 않아 'nunchi 게임 스케줄 실행 예외'에 해당한다
