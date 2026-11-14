"""블라인드 리뷰 Gemini 채점 v2 — 비공개 패키지 구조 해석 후 채점 (2026-10-30).

private_key.json: blind_id → {app, case_id, category, injected_defect, detection_keyword}
verification.json: {cases: [{app, id, category, type, ...}]}
결과: blind_id 별로 detection_keyword 가 응답 원문에 있으면 1점 (80점 만점)
"""
import base64, json, zlib
from pathlib import Path

JUDGE_PATH = Path("/data/vm_project/haness/apps/blind_review_judge_20261027/private_judge.b64")
raw = "".join(JUDGE_PATH.read_text().split())
pkg = json.loads(zlib.decompress(base64.b64decode(raw)))

private_key = json.loads(pkg["private_key.json"])
verification = json.loads(pkg["verification.json"])

RESULT_DIR = Path("/data/vm_project/haness/apps/blind_review_20261027/results/gemini/jobs/cc319de2752c4649a13e1834a2c0c864")
results = {}
for f in sorted(RESULT_DIR.glob("*.json")):
    if f.name == "summary.json": continue
    r = json.loads(f.read_text()); results[r["id"]] = r

print(f"결과: {len(results)}건, 비공개 키: {len(private_key)}건")

detected = 0; missed = []; normal_fps = 0; normal_count = 0; details = []

for blind_id, info in sorted(private_key.items()):
    response_text = results.get(blind_id, {}).get("response", "")
    case_id = info.get("case_id", ""); app_name = info.get("app", ""); category = info.get("category", "")
    defect_desc = info.get("injected_defect") or info.get("description") or ""
    is_normal = info.get("type") in ("normal","clean","correct","baseline") or "normal" in case_id.lower() or "clean" in case_id.lower()
    keywords = info.get("detection_keyword") or info.get("detection_keywords") or info.get("keywords") or []
    if isinstance(keywords, str): keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    if not keywords and defect_desc: keywords = [defect_desc]
    found = any(kw.lower() in response_text.lower() for kw in keywords) if keywords else False
    if is_normal:
        normal_count += 1
        if found: normal_fps += 1; details.append({"id":blind_id,"case":case_id,"type":"FALSE_POS","app":app_name})
    else:
        if found: detected += 1; details.append({"id":blind_id,"case":case_id,"type":"DETECTED","app":app_name,"cat":category})
        else: missed.append({"id":blind_id,"case":case_id,"app":app_name,"cat":category,"defect":defect_desc[:60]})

total_defects = len(private_key) - normal_count
print(f"\n=== Gemini 3.8-flash 채점 ===")
print(f"결함: {total_defects}건, 정상 대조: {normal_count}건")
print(f"검출: {detected}/{total_defects} ({detected}점)")
print(f"검출율: {detected/total_defects*100:.1f}%" if total_defects else "N/A")
print(f"오진: {normal_fps}/{normal_count}")
print(f"미검출: {len(missed)}건")

cats={}; cat_total={}
for d in details:
    if d["type"]=="DETECTED": cats[d.get("cat","?")]=cats.get(d.get("cat","?"),0)+1
for info in private_key.values():
    if info.get("type") not in ("normal","clean","correct","baseline") and "normal" not in info.get("case_id","").lower() and "clean" not in info.get("case_id","").lower():
        c=info.get("category","?"); cat_total[c]=cat_total.get(c,0)+1
print(f"\n=== 범주별 ===")
for c in sorted(set(list(cats)+list(cat_total))): print(f"  {c}: {cats.get(c,0)}/{cat_total.get(c,0)}")
if missed:
    print(f"\n=== 미검출 상위 10건 ===")
    for m in missed[:10]: print(f"  {m['case']} ({m['app']}) — {m['defect']}")
output={"provider":"gemini","model":"gemini-3.8-flash","job_id":"cc319de2752c4649a13e1834a2c0c864","total_defects":total_defects,"detected":detected,"score":detected,"max_score":total_defects,"normal_count":normal_count,"false_positives":normal_fps,"missed_count":len(missed),"by_category":{c:{"detected":cats.get(c,0),"total":cat_total.get(c,0)} for c in cat_total},"missed":missed}
out_path=RESULT_DIR/"score.json"; out_path.write_text(json.dumps(output,ensure_ascii=False,indent=2))
print(f"\n점수 저장: {out_path}")
