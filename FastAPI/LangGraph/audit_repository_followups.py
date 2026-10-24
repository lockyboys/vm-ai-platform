"""미완료 Repository 항목을 SELECT로만 조사한다. 실제 값은 변경하지 않는다."""
import datetime, json, sys
from pathlib import Path
ROOT=Path("/data/vm_project")
sys.path.insert(0,str(ROOT))
from common.database import CommonDatabase
from common.common_function import write_json_atomic
def main():
    evidence={"checked_at":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()}
    common=CommonDatabase(database_role="COMMON",connect_mongodb=False)
    story=CommonDatabase(database_role="STORY",connect_mongodb=False)
    try:
        queries={
          "source_audit_object":(story,"SELECT object_id,object_code,object_name,target_identifier_field,identifier_target_code,sequence_scope_code,active_yn,status_code FROM sp_object WHERE object_code=%s AND deleted_dt IS NULL",("SOURCE_AUDIT",)),
          "legacy_session":(common,"SELECT user_id,task_type,learning_type,COUNT(*) AS row_count FROM harness_source_audit WHERE user_id=%s GROUP BY user_id,task_type,learning_type",("claude-opus-5-5_20261024_000212",)),
          "storage_contracts":(common,"SELECT group_code,code,common_code_json,status_code FROM cm_common_code WHERE group_code=%s AND deleted_dt IS NULL",("STORAGE_SEPARATION_TARGET",)),
          "identifier_contracts":(common,"SELECT group_code,code,common_code_json FROM cm_common_code WHERE common_code_json LIKE %s AND deleted_dt IS NULL",("%table_identifier_metadata%",)),
          "pipeline_queries":(common,"SELECT query_id,query_name,crud_type,verified_yn,status_code FROM cm_verified_sql_query WHERE query_name LIKE %s AND deleted_dt IS NULL",("%pipeline_results%",)),
        }
        for name,(db,sql,params) in queries.items():
            try:evidence[name]=db.fetch_all(sql,params)
            except Exception as exc:evidence[name]={"error_type":type(exc).__name__}
        for label,db in [("COMMON",common),("STORY",story)]:
            evidence[label+"_payload_tables"]=db.fetch_all("SELECT table_name, table_comment FROM information_schema.tables WHERE table_schema=%s AND table_comment LIKE %s",(db.database_name,"%MONGODB_PAYLOAD%"))
        evidence["mongo_api"]=[n for n in dir(CommonDatabase) if any(s in n for s in ("find","count","collection")) and not n.startswith("_")]
    finally:
        common.close();story.close()
    path=ROOT/"harness/memory/repository_followup_audit_20261025.json"
    write_json_atomic(path,evidence)
    summary={k:v for k,v in evidence.items() if k in ("source_audit_object","legacy_session","pipeline_queries","mongo_api")}
    rows=evidence.get("identifier_contracts")
    if isinstance(rows,list):
        summary["audit_identifier_contracts"]=[]
        for r in rows:
            j=r["common_code_json"]
            if isinstance(j,str):j=json.loads(j)
            summary["audit_identifier_contracts"].append({"group_code":r["group_code"],"code":r["code"],"audit_metadata":j.get("table_identifier_metadata",{}).get("harness_source_audit")})
    summary["storage_contract_count"]=len(evidence["storage_contracts"]) if isinstance(evidence.get("storage_contracts"),list) else evidence.get("storage_contracts")
    summary["payload_table_counts"]={label:len(evidence[label+"_payload_tables"]) for label in ("COMMON","STORY")}
    summary["evidence_path"]=str(path)
    print(json.dumps(summary,ensure_ascii=False,default=str))
if __name__=="__main__":main()
