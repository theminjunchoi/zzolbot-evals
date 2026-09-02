"""환각 검사를 변형 프로브로 검증한다. judge를 부르지 않는다.

라벨은 구성 방식이 정한다. component-swap은 정의상 환각이고, unmutated와
benign-paraphrase와 vague-cause는 정의상 환각이 아니다.

정답 답변은 학습 데이터의 교사 출력을 쓴다. 골든셋 시나리오에 대응하는 검증된 답이다.
"""
import json
from pathlib import Path
from harness.domain import Analysis
from harness.loading import ScenarioLoader
from harness.formatting import AnswerFormatter
from analysis.mutations import build_probes, MUTATION_SETS, FlatAnswer
from training.verification import NoFabricatedIdentifiers, IdentifiersAreGrounded

TARGETS = {"component-swap"}                       # 잡아야 하는 것
CONTROLS = {"unmutated", "benign-paraphrase", "vague-cause"}   # 잡으면 안 되는 것

scen = {s.name: s for s in ScenarioLoader().load_dir(Path("golden-set/monitor"))}
fmt = AnswerFormatter()

# 정답 답변의 출처: **골든셋에서 만점 받은 모델 출력**.
# 학습 데이터의 교사 출력은 못 쓴다. 골든셋이 학습 데이터에서 의도적으로 배제돼 있어
# (중복 감사 4겹, 0건) 짝지을 수 있는 것이 없다. 감사가 제대로 작동한 결과다.
# 만점(1.00)은 스키마, 판정, 인용이 전부 통과했다는 뜻이라 대조군 기준으로 적합하다.
from harness.local_model import extract_json
answers = {}
for src in ("size-3b", "adp-mlx"):
    f = Path(f"reports/runs/{src}-raw.jsonl")
    if not f.exists():
        continue
    for line in f.open():
        r = json.loads(line)
        if r["arm"] in ("trained", "v6") and r["score"] >= 1.0 and r["scenario"] not in answers:
            answers[r["scenario"]] = extract_json(r["raw"])
print(f"만점 받은 모델 출력으로 확보한 시나리오 {len(answers)}종")

rule_new, rule_old = NoFabricatedIdentifiers(), IdentifiersAreGrounded()
rows = []
for name, ans in answers.items():
    s = scen[name]
    try:
        d = json.loads(ans)
    except Exception:
        continue
    # AnswerFormatter는 evidence_found가 아니라 **grounded**(접지 검증 후)를 렌더한다.
    # 지표 정의표의 "오탐 접지 전/후" 구분이 여기서도 나온다. 만점(1.00)은 인용 검증까지
    # 통과했다는 뜻이므로 양성이면 grounded=True다.
    ev = bool(d.get("evidenceFound"))
    flat_src = fmt.flatten(Analysis(
        summary=d.get("summary", ""), root_cause_hypothesis=d.get("rootCauseHypothesis", ""),
        suggested_actions=tuple(d.get("suggestedActions", [])),
        evidence_found=ev, evidence_line=d.get("evidenceLine", ""), grounded=ev))
    for p in build_probes(name, flat_src, MUTATION_SETS["all"], s.rubric):
        fa = FlatAnswer.parse(p.answer)
        if fa is None:
            continue
        # FlatAnswer는 evidence_line을 안 들고 있다(평탄화에서 빠진다).
        # 환각 규칙은 인용을 안 보므로 빈 값으로 둔다.
        an = Analysis(summary=fa.summary, root_cause_hypothesis=fa.cause,
                      suggested_actions=(fa.actions_block,),
                      evidence_found=fa.evidence_found, evidence_line="")
        rows.append((p.mutation, bool(rule_new.violations(s, an)), bool(rule_old.violations(s, an))))

from collections import Counter
agg = {}
for m, new, old in rows:
    a = agg.setdefault(m, [0, 0, 0]); a[0] += 1; a[1] += new; a[2] += old
print()
print(f"{'변형':22} {'n':>4} {'신규 규칙':>10} {'기존 규칙':>10}  기대")
for m in sorted(agg):
    n, new, old = agg[m]
    exp = "잡아야" if m in TARGETS else ("잡으면 안 됨" if m in CONTROLS else "-")
    print(f"{m:22} {n:>4} {new:>10} {old:>10}  {exp}")

tgt = [(m, a) for m, a in agg.items() if m in TARGETS]
ctl = [(m, a) for m, a in agg.items() if m in CONTROLS]
tn = sum(a[0] for _, a in tgt); td = sum(a[1] for _, a in tgt)
cn = sum(a[0] for _, a in ctl); cd = sum(a[1] for _, a in ctl)
print()
print(f"검출  {td}/{tn}" + (f" = {td/tn*100:.0f}%" if tn else ""))
print(f"오탐  {cd}/{cn}")
print()
if cd > 0:      print("판정: **기각** (대조군 오탐이 1건이라도 있으면 기각)")
elif tn and td/tn >= 0.6: print("판정: **채택**")
else:           print("판정: **보류** (오탐 0이나 검출 60% 미만)")
