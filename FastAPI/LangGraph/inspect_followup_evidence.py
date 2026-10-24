"""저장된 조사 근거에서 계약과 실패 PDF 목록만 읽고 요약한다."""
import inspect,json,sys
from pathlib import Path
ROOT=Path("/data/vm_project");sys.path.insert(0,str(ROOT))
from common.database import CommonDatabase
p=ROOT/"harness/memory/repository_followup_audit_20261025.json"
j=json.loads(p.read_text())
for r in j["storage_contracts"]:
    v=r["common_code_json"]
    if isinstance(v,str):v=json.loads(v)
    print(json.dumps({"code":r["code"],"status":r["status_code"],"source":v.get("source_table_name"),"collection":v.get("mongodb_collection_name")},ensure_ascii=False))
print("COUNT_SIGNATURE",inspect.signature(CommonDatabase.count_documents))
out=ROOT/"outputs/insurance_docs/db_insurance_terms"
print("OUTPUT_FILES",json.dumps([p.name for p in out.glob("*.json")],ensure_ascii=False))
for p in out.glob("*.json"):
    if any(x in p.name for x in ["fail","result","manifest"]):
        v=json.loads(p.read_text())
        rows=v if isinstance(v,list) else v.get("results",v.get("files",[])) if isinstance(v,dict) else []
        failed=[r for r in rows if isinstance(r,dict) and (r.get("status") in ("FAILED","failed","ERROR","error") or r.get("success") is False)]
        print(json.dumps({"file":p.name,"rows":len(rows),"failed":failed[:3]},ensure_ascii=False))
