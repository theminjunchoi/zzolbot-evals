# 재생 측정 36-prod-replay

시나리오 148종 (양성 74, 음성 74)

### 음성 (알림과 무관한 로그 · 정답은 근거 없음) (74종)

| 지표 | Gemini | 자체 모델 |
|---|---|---|
| 형식 실패 | 0 | 0 |
| 근거 주장(접지 전) | 27 | 25 |
| 접지 통과 | 25 | 25 |

### 양성 (알림과 맞는 로그 · 라벨 없음) (74종)

| 지표 | Gemini | 자체 모델 |
|---|---|---|
| 형식 실패 | 0 | 0 |
| 근거 주장(접지 전) | 54 | 48 |
| 접지 통과 | 50 | 48 |

### 두 모델 일치

접지 후 판정 일치 90/148 (61%)

불일치 시나리오(손 검토 대상):

```text
replay-pos-002
replay-pos-004
replay-neg-004
replay-pos-005
replay-neg-008
replay-pos-009
replay-neg-009
replay-pos-011
replay-neg-012
replay-pos-014
replay-neg-015
replay-pos-018
replay-neg-018
replay-pos-019
replay-pos-020
replay-pos-021
replay-neg-022
replay-pos-023
replay-pos-024
replay-neg-024
replay-pos-025
replay-neg-027
replay-pos-031
replay-pos-033
replay-neg-033
replay-neg-034
replay-neg-036
replay-neg-037
replay-neg-039
replay-pos-040
replay-neg-040
replay-pos-044
replay-neg-045
replay-pos-046
replay-neg-046
replay-neg-047
replay-pos-048
replay-pos-049
replay-neg-049
replay-neg-050
replay-pos-051
replay-pos-053
replay-pos-054
replay-neg-055
replay-pos-056
replay-neg-058
replay-pos-061
replay-neg-061
replay-pos-062
replay-neg-064
replay-neg-065
replay-pos-067
replay-neg-067
replay-pos-068
replay-pos-069
replay-pos-070
replay-pos-071
replay-pos-072
```