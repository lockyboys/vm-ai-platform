"""테이블 COMMENT에 선언된 실제 payload 컬렉션을 읽기 전용으로 검증한다."""
import json,re,sys
from pathlib import Path
ROOT=Path("/data/vm_project");sys.path.insert(0,str(ROOT))
from common.database import CommonDatabase
from common.common_function import now_kst_iso,write_json_atomic
saved=json.loads((ROOT/"harness/memory/repository_followup_audit_20261025.json").read_text())
sources={};mongos={};results=[]
try:
    for role in ("COMMON","STORY"):
        db=sources.setdefault(role,CommonDatabase(database_role=role,connect_mongodb=False))
        for row in saved[role+"_payload_tables"]:
            table=row["table_name"];comment=row["table_comment"]
            r={"role":role,"table":table}
            try:
                collection=re.search(r"Collection:\s*([^;\s]+)",comment).group(1)
                mrole=re.search(r"MongoDB Role:\s*([^;\s]+)",comment).group(1)
                r.update({"collection":collection,"mongo_role":mrole})
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",table):raise ValueError("Invalid table")
                if mrole not in mongos:mongos[mrole]=CommonDatabase(database_role=mrole,connect_mariadb=False,connect_mongodb=True)
                mongo=mongos[mrole]
                total=db.fetch_one("SELECT COUNT(*) AS n FROM `"+table+"`",())["n"]
                r["source_rows"]=total;r["payload_documents"]=mongo.count_documents(collection)
                doc=mongo.find_one(collection,{})
                r["payload_keys"]=sorted(doc.keys()) if doc else []
                meta=(doc or {}).get("_sps",{})
                r["source_metadata_keys"]=sorted(meta.keys()) if isinstance(meta,dict) else []
                r["documents_tagged_with_table"]=mongo.count_documents(collection,{"_sps.source_table_name":table})
                r["count_matches"]=r["source_rows"]==r["payload_documents"]
            except Exception as e:r["error_type"]=type(e).__name__
            results.append(r)
finally:
    for db in [*sources.values(),*mongos.values()]:db.close()
evidence={"checked_at":now_kst_iso(),"results":results}
write_json_atomic(ROOT/"harness/memory/physical_payload_verification_20261025.json",evidence)
print(json.dumps(evidence,ensure_ascii=False))
