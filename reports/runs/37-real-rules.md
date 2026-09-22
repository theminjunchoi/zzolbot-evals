# 재생 측정 37-real-rules

시나리오 147종 (양성 73, 음성 74)

### 음성 (알림과 무관한 로그 · 정답은 근거 없음) (74종)

| 지표 | Gemini | 자체 모델 |
|---|---|---|
| 형식 실패 | 0 | 0 |
| 근거 주장(접지 전) | 0 | 55 |
| 접지 통과 | 0 | 55 |

### 양성 (알림과 맞는 로그 · 라벨 없음) (73종)

| 지표 | Gemini | 자체 모델 |
|---|---|---|
| 형식 실패 | 0 | 0 |
| 근거 주장(접지 전) | 53 | 60 |
| 접지 통과 | 50 | 60 |

### 두 모델 일치

접지 후 판정 일치 68/147 (46%)

불일치 시나리오(손 검토 대상):

```text
replay-pos-000
replay-neg-000
replay-pos-002
replay-neg-002
replay-neg-003
replay-neg-004
replay-neg-006
replay-neg-007
replay-neg-008
replay-neg-010
replay-pos-011
replay-pos-012
replay-neg-012
replay-neg-013
replay-pos-014
replay-neg-014
replay-neg-015
replay-pos-016
replay-neg-016
replay-neg-017
replay-neg-018
replay-neg-019
replay-neg-020
replay-neg-021
replay-neg-022
replay-pos-024
replay-neg-024
replay-pos-025
replay-pos-026
replay-neg-026
replay-neg-027
replay-neg-028
replay-neg-029
replay-pos-030
replay-neg-030
replay-neg-031
replay-neg-032
replay-neg-033
replay-neg-034
replay-pos-036
replay-neg-036
replay-neg-037
replay-pos-038
replay-neg-038
replay-pos-039
replay-neg-040
replay-neg-042
replay-pos-044
replay-neg-044
replay-neg-045
replay-neg-046
replay-neg-048
replay-pos-049
replay-neg-049
replay-neg-050
replay-pos-052
replay-neg-052
replay-neg-054
replay-pos-055
replay-pos-056
replay-neg-056
replay-neg-057
replay-neg-058
replay-neg-059
replay-pos-060
replay-neg-060
replay-pos-062
replay-neg-062
replay-neg-063
replay-neg-064
replay-pos-065
replay-neg-066
replay-neg-067
replay-pos-068
replay-neg-068
replay-neg-070
replay-pos-071
replay-pos-072
replay-neg-072
```