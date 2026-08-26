## 합성 필터 통계

- 생성 시도: 24건, 생존: 22건 (92%)

| 검증기 | 탈락 건수 |
|---|---|
| screen | 2 |

### 탈락 사유 상세

- `monitor-5xx-qr-storage-upload-failure-1043` [screen] 채점 기준은 로그가 'POST /rooms 요청이 StorageUploadException으로 5xx를 반환했음'을 보여준다고 서술했으나, 실제 로그에는 해당 요청이 StorageUploadException으로 실패했음만 나타나고 HTTP 5xx 상태 코드를 직접적으로 반환했다는 내용은 없습니다.
- `monitor-stream-latency-minigame-start-mixed-1048` [screen] 채점 기준은 MiniGameStartConsumer의 이벤트 처리 실패가 세 차례 발생했다고 서술했지만, 실제 로그에는 네 차례 발생한 것으로 나타나 모순됩니다.
