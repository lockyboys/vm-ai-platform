"""활성 페이로드 계약과 실제 MariaDB/MongoDB를 읽기 전용으로 비교한다."""
import datetime,json,re,sys
from pathlib import Path
ROOT=Path("/data/vm_project");sys.path.insert(0,str(ROOT))
from common.database import CommonDatabase
from common.common_function import write_json_atomic
def safe_name(name):
    if not isinstance(name,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",name):raise ValueError("Invalid Repository identifier")
    return name
def main():
    saved=json.loads((ROOT/"harness/memory/repository_followup_audit_20261025.json").read_text())
    sources={};mongos={};results=[]
    try:
        for row in saved["storage_contracts"]:
            if row["status_code"]!="ACTIVE":continue
            c=row["common_code_json"];c=json.loads(c) if isinstance(c,str) else c
            r={"code":row["code"],"table":c["source_table_name"],"collection":c["mongodb_collection_name"]}
            try:
                role=c["source_database_role"];mrole=c["mongodb_database_role"]
                if role not in sources:sources[role]=CommonDatabase(database_role=role,connect_mongodb=False)
                if mrole not in mongos:mongos[mrole]=CommonDatabase(database_role=mrole,connect_mariadb=False,connect_mongodb=True)
                db=sources[role];mongo=mongos[mrole]
                table=safe_name(c["source_table_name"]);key=safe_name(c["source_identifier_column_name"])
                columns=db.fetch_all("SELECT column_name,column_comment,data_type FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",(db.database_name,table))
                r["table_exists"]=bool(columns)
                r["mongo_total"]=mongo.count_documents(c["mongodb_collection_name"])
                r["mongo_source_tagged"]=mongo.count_documents(c["mongodb_collection_name"],{"_sps.source_table_name":table})
                names={x["column_name"] for x in columns}
                r["payload_columns_remaining"]=[x for x in c.get("payload_column_names",[]) if x in names]
                if columns:
                    ids=db.fetch_all("SELECT `"+key+"` AS source_id FROM `"+table+"`",())
                    r["source_rows"]=len(ids)
                    missing=0
                    for item in ids:
                        val=item["source_id"]
                        query={"_sps.source_table_name":table,"_sps.source_identifier":{"$in":list(dict.fromkeys([val,str(val)]))}}
                        if mongo.count_documents(c["mongodb_collection_name"],query)==0:missing+=1
                    r["source_rows_without_tagged_payload"]=missing
                    r["contract_consistent"]=missing==0 and not r["payload_columns_remaining"]
                else:r["contract_consistent"]=False
            except Exception as exc:r["error_type"]=type(exc).__name__;r["contract_consistent"]=False
            results.append(r)
    finally:
        for db in [*sources.values(),*mongos.values()]:db.close()
    evidence={"checked_at":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
              "results":results,"all_active_contracts_consistent":all(r.get("contract_consistent") for r in results)}
    path=ROOT/"harness/memory/payload_contract_verification_20261025.json";write_json_atomic(path,evidence)
    print(json.dumps({**evidence,"evidence_path":str(path)},ensure_ascii=False))
if __name__=="__main__":main()
