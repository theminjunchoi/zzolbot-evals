"""인용 제약을 GBNF 문법으로 옮긴다. llama.cpp가 트라이 대신 문법을 받기 때문이다.

`harness/constrained.py`의 트라이는 mlx와 torch의 로짓 프로세서 규약에 맞춰져 있다.
llama.cpp는 프로세서를 꽂을 자리가 없고 대신 GBNF를 받는다. **같은 것을 강제하되 수단이
다르다.**

강제하는 계약은 트라이와 같다.

- `evidenceLine`은 **주어진 로그 줄 그대로**이거나 **빈 문자열**이다. 빈 문자열을 막으면
  근거 없음이 정답인 시나리오에서 모델이 억지로 로그를 쓰다 JSON을 못 닫는다(리포트 14번)
- 인용이 닫히면 객체를 닫는 것 말고 할 수 있는 것이 없다. 안 그러면 필드를 다시 쓰는
  반복 생성에 빠진다(리포트 15번에서 3건)

**트라이와 다른 점이 하나 있고, 그것이 이 방식의 대가다.** GBNF는 출력 전체를 문법으로
서술해야 하므로 앞 네 필드의 **순서까지 고정된다.** 트라이는 마커를 만나기 전에는 아무것도
강제하지 않는다. 시스템 프롬프트가 이 순서로 스키마를 제시하므로 실제 출력도 그 순서지만,
**강제와 관찰은 다르다.** 대조할 때 이 차이를 효과로 오독하면 안 된다.
"""

from __future__ import annotations

import json

#: JSON 문자열 본문 한 글자. 따옴표와 역슬래시는 이스케이프로만 등장한다
_JSON_CHAR = r'''[^"\\] | "\\" ["\\/bfnrt] | "\\u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]'''


def _literal(text: str) -> str:
    """GBNF 문자열 리터럴로 감싼다.

    두 겹의 이스케이프가 겹치는 자리라 실수하기 쉽다. 들어오는 값은 이미 **JSON 본문**이라
    따옴표가 `\\"` 두 글자로 들어 있고, GBNF 리터럴 안에서 그 역슬래시를 또 escape 해야 한다.
    """
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def citation_grammar(log_samples: list[str]) -> str:
    """로그 줄 목록으로 응답 전체의 문법을 만든다."""
    bodies = [json.dumps(line, ensure_ascii=False)[1:-1] for line in log_samples]
    # 중복 줄이 있으면 문법이 커지기만 하고 허용 집합은 같다
    unique = list(dict.fromkeys(bodies))
    alts = " | ".join(f"line{i}" for i in range(len(unique))) or '"\\u0000"'
    lines = "\n".join(f"line{i} ::= {_literal(body)}" for i, body in enumerate(unique))

    # **규칙은 한 줄에 하나씩 쓴다.** 괄호 밖에서는 줄바꿈이 규칙의 끝이라,
    # 보기 좋게 여러 줄로 쪼개면 "failed to parse grammar"가 난다. 실제로 겪었다.
    root = ('root ::= "{" ws "\\"summary\\":" ws str "," ws '
            '"\\"rootCauseHypothesis\\":" ws str "," ws '
            '"\\"suggestedActions\\":" ws arr "," ws '
            '"\\"evidenceFound\\":" ws bool "," ws '
            '"\\"evidenceLine\\":" ws cite ws "}"')

    return "\n".join([
        root,
        'cite ::= "\\"\\"" | "\\"" anyline "\\""',
        f"anyline ::= {alts}",
        lines,
        'str ::= "\\"" char* "\\""',
        f"char ::= {_JSON_CHAR}",
        'arr ::= "[" ws (str (ws "," ws str)*)? ws "]"',
        'bool ::= "true" | "false"',
        r'ws ::= [ \t\n]*',
        "",
    ])
