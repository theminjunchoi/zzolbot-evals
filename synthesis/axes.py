"""시나리오 난이도 축 정의. 생성 프롬프트가 이 명세를 그대로 사용한다.

새 축은 Axis 항목 추가로 확장한다. 기존 20종이 포화시킨 축(unrelated, layer 등)보다
신규 축(partial, compound, borderline, near-miss)의 난이도가 높다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Axis:
    key: str
    expected: str  # "예" | "아니오"
    min_logs: int
    max_logs: int
    instruction: str


AXES: dict[str, Axis] = {a.key: a for a in [
    Axis("positive-dense", "예", 6, 12,
         "알림과 직접 관련된 에러가 알림 시각과 정합하는 좁은 시간창(5분 이내)에 밀집 반복된다. "
         "봇은 근거를 인정하고 원인을 짚어야 한다."),
    Axis("unrelated-trap", "아니오", 2, 4,
         "알림과 무관한 도메인의 산발적 에러만 주어진다. 봇이 무관한 로그를 원인으로 지어내면 안 된다."),
    Axis("stale-reingested", "아니오", 6, 10,
         "조회 창은 최근 30분인데 로그 본문 타임스탬프는 전날 여러 시각에 흩어져 있다(재적재 아티팩트). "
         "마지막 1줄 정도만 현재 시각이다. 봇은 타임스탬프 불일치를 지적해야 한다."),
    Axis("sparse-evidence", "아니오", 1, 2,
         "수십 건 급증 알림에 로그가 1~2줄뿐이고 서로 시간이 동떨어져 있다. 표본 부족을 인정해야 한다."),
    Axis("partial-relevance", "예", 6, 10,
         "관련 에러(밀집)와 무관 에러(산발)가 섞여 있다. 봇은 관련 로그만 근거로 삼아 원인을 짚어야 하고, "
         "무관 로그를 원인에 끌어들이면 오답이다. rubric에 어느 로그가 관련이고 어느 것이 무관인지 명시하라."),
    Axis("compound-cause", "예", 6, 12,
         "근본 원인 장애(예: Redis 연결 실패)와 그 파급 증상(예: 스트림 처리 오류, 요청 실패)이 함께 나타난다. "
         "봇은 파급 증상이 아니라 근본 원인을 가설로 짚어야 정답이다. rubric에 근본/파급 구분을 명시하라."),
    Axis("borderline-window", "아니오", 3, 6,
         "로그 시각이 조회 창(30분)을 살짝 벗어난 40~90분 전에 몰려 있다. 알림 시각과의 어긋남이 미묘해서 "
         "주의 깊게 봐야 알 수 있다. 봇은 시각 불일치로 근거 불충분 판정을 해야 한다."),
    Axis("near-miss-component", "아니오", 3, 6,
         "알림과 같은 계열이지만 다른 컴포넌트의 에러가 주어진다(예: DB 커넥션 풀 알림에 Redis 연결 에러, "
         "정산 스트림 적체 알림에 카드게임 스트림 에러). 표면적으로 그럴듯해 보여도 알림의 대상 컴포넌트를 "
         "설명하지 못하므로 근거로 삼으면 오답이다. rubric에 왜 다른 컴포넌트인지 명시하라."),
]}
