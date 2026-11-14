"""블라인드 리뷰 Gemini 채점 v3 — LLM 판독 기반 (2026-10-30).

SCORING.md 기준: "실제 변경 위치/연산과 그 문제를 구체적으로 지적하면 1점"
→ description(addition, subtraction 등)이 응답에 있는지가 아니라,
   해당 연산의 결함(예: 덧셈 결과가 틀림)을 구체적으로 짚었는지 LLM이 판독해야 한다.
→ verification.json 의 cases 에 더 상세한 결함 정보가 있을 수 있으므로 함께 출력한다.

이 스크립트는 채점 판독에 필요한 데이터 패키지를 만들어 파일로 저장한다.
82건 전체를 한 번에 출력하면 토큰이 넘치므로, 범주(category)별로 분리해 저장한다.
"""
import base64, json, zlib
from pathlib import Path

pkg = json.loads(zlib.decompress(base64.b64decode("".join(Path("/data/vm_project/haness/apps/blind_review_judge_20261027/private_judge.b64").read_text().split()))))
private_key = json.loads(pkg["private_key.json"])
verification = json.loads(pkg["verification.json"])

RESULT_DIR = Path("/data/vm_project/haness/apps/blind_review_20261027/results/gemini/jobs/cc319de2752c4649a13e1834a2c0c864")
OUT_DIR = RESULT_DIR / "scoring_packages"
OUT_DIR.mkdir(exist_ok=True)

results = {}
for f in sorted(RESULT_DIR.glob("*.json")):
    if f.name in ("summary.json", "score.json"): continue
    r = json.loads(f.read_text()); results[r["id"]] = r

# verification.json 의 cases 를 case_id 로 인덱싱
ver_by_id = {}
for c in verification.get("cases", []):
    ver_by_id[c["id"]] = c

# 범주별로 분리
by_cat = {}
for blind_id, info in private_key.items():
    cat = info.get("category", "unknown")
    entry = {
        "blind_id": blind_id,
        "app": info.get("app"),
        "case_id": info.get("case_id"),
        "description": info.get("description"),
        "verification": ver_by_id.get(info.get("case_id"), {}),
        "response": results.get(blind_id, {}).get("response", "")[:3000],  # 응답 앞 3000자
        "success": results.get(blind_id, {}).get("success"),
    }
    by_cat.setdefault(cat, []).append(entry)

for cat, entries in sorted(by_cat.items()):
    path = OUT_DIR / f"{cat}.json"
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2))
    print(f"{cat}: {len(entries)}건 → {path.name}")

# 전체 요약
print(f"\n총 {len(private_key)}건을 {len(by_cat)}개 범주로 분리 → {OUT_DIR}")
print("SCORING.md 기준에 따라 각 범주 파일의 response 에서 구체적 결함 지적 여부를 판독해야 합니다.")
