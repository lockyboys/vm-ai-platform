"""Record the approved lifecycle Rule in common codes without enabling it.
Only INSERTs a dedicated group (if absent) and the one requested code.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from common.database import CommonDatabase

RULE_CODE = "RL_PAYLOAD_WRITE_LIFECYCLE_V1"
GROUP_CODE = "SPS_PAYLOAD_POLICY"
ROOT = Path(__file__).resolve().parents[2]

def digest(value):
    """Use deterministic snapshots to detect changes between preview and apply."""
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()

def save(kind,value,stamp):
    """Evidence is immutable; never overwrite a previous run."""
    path=ROOT / ("harness/memory/payload_lifecycle_common_code_"+kind+"_"+stamp+".json")
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,default=str)
    return str(path)

def main():
    request=json.loads(sys.stdin.read() or "{}")
    mode=request.get("mode","plan")
    if mode not in ("plan","apply"):
        raise ValueError("mode must be plan or apply")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    with CommonDatabase(database_role="COMMON") as db:
        schemas={}
        for table in ("cm_common_code","cm_common_code_group","rl_rule"):
            schemas[table]=db.fetch_one("SHOW CREATE TABLE "+table)
            comments=db.fetch_all(
                "SELECT column_name,column_comment FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s",(db.database_name,table))
            if not comments or any(not x["column_comment"] for x in comments):
                raise ValueError("Missing column COMMENT: "+table)
        rule=db.fetch_one("SELECT * FROM rl_rule WHERE rule_code=%s AND deleted_dt IS NULL",(RULE_CODE,))
        if not rule or rule["status_code"]!="DRAFT" or json.loads(rule["remark"]).get("enforced") is not False:
            raise ValueError("Expected recorded non-enforced DRAFT Rule")
        for code in ("DRAFT","CREATE_MAINTAIN"):
            group="STATUS_CODE" if code=="DRAFT" else "COMMON_CODE_LIFECYCLE_STATUS"
            if not db.fetch_one(
                "SELECT code FROM cm_common_code WHERE group_code=%s AND code=%s "
                "AND status_code=%s AND deleted_dt IS NULL",(group,code,"ACTIVE")):
                raise ValueError("Missing active status contract: "+code)
        group=db.fetch_one("SELECT * FROM cm_common_code_group WHERE group_code=%s",(GROUP_CODE,))
        existing=db.fetch_all("SELECT * FROM cm_common_code WHERE code=%s",(RULE_CODE,))
        if existing:
            print(json.dumps({"already_exists":True,"rows":existing,"writes":0},ensure_ascii=False,default=str))
            return
        if group and (group["deleted_dt"] is not None or group["group_name"]!="SPS Payload 정책"):
            raise ValueError("Existing group needs review; never overwrite it")
        state={"rule":rule,"group":group,"existing":existing}
        payload={
            "contract_kind":"PAYLOAD_POLICY_RECORD",
            "rule_reference":{"table":"rl_rule","rule_id":rule["rule_id"],"rule_code":RULE_CODE,
                              "version_num":rule["version_num"],"snapshot_sha256":digest(rule)},
            "policy_snapshot":{"description":rule["rule_description"],
                               "record":json.loads(rule["remark"])},
            "record_mode":"DOCUMENT_ONLY","enforced":False,
            "rollout_phase":"RECORD","runtime_integration":"NOT_APPLIED",
            "registration_origin":"CODEX via local CommonDatabase; client_ip is execution host loopback",
            "change_policy":"Preserve Rule as authority; review and version changes before activation"
        }
        plan={"group_code":GROUP_CODE,"code":RULE_CODE,"status_code":"DRAFT",
              "enforced":False,"create_group":group is None,
              "before":state,"schemas":schemas,"common_code_json":payload}
        plan_hash=digest(plan)
        evidence=save("plan" if mode=="plan" else "before",plan,stamp)
        if mode=="plan":
            print(json.dumps({"success":True,"dry_run":True,"writes":0,
                              "plan_hash":plan_hash,"group_code":GROUP_CODE,"code":RULE_CODE,
                              "create_group":group is None,"evidence":evidence},ensure_ascii=False))
            return
        if request.get("expected_plan_hash")!=plan_hash:
            raise ValueError("Plan changed or not reviewed")
        db.begin()
        try:
            locked_rule=db.fetch_one("SELECT * FROM rl_rule WHERE rule_code=%s FOR UPDATE",(RULE_CODE,))
            locked_group=db.fetch_one("SELECT * FROM cm_common_code_group WHERE group_code=%s FOR UPDATE",(GROUP_CODE,))
            locked_codes=db.fetch_all("SELECT * FROM cm_common_code WHERE code=%s FOR UPDATE",(RULE_CODE,))
            if {"rule":locked_rule,"group":locked_group,"existing":locked_codes}!=state:
                raise ValueError("Concurrent modification; stop without overwriting")
            if group is None:
                n=db.execute(
                    "INSERT INTO cm_common_code_group "
                    "(group_code,group_name,group_description,status_code,reserved_yn,system_yn,"
                    "created_by,program_id,client_ip,lifecycle_status_code) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (GROUP_CODE,"SPS Payload 정책",
                     "MariaDB·MongoDB Payload 저장 정책의 Rule 참조와 기록을 관리한다. DRAFT 기록 전용이며 자동 강제 적용을 의미하지 않는다.",
                     "DRAFT","N","Y","CODEX","PAYLOAD_LIFECYCLE_COMMON_CODE_20261025",
                     "127.0.0.1","CREATE_MAINTAIN"))
                if n!=1: raise RuntimeError("Group INSERT mismatch")
            n=db.execute(
                "INSERT INTO cm_common_code "
                "(group_code,code,code_name,common_code_description,status_code,common_code_json,"
                "created_by,program_id,client_ip,lifecycle_status_code) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (GROUP_CODE,RULE_CODE,rule["rule_name"],
                 rule["rule_description"],"DRAFT",json.dumps(payload,ensure_ascii=False),
                 "CODEX","PAYLOAD_LIFECYCLE_COMMON_CODE_20261025","127.0.0.1","CREATE_MAINTAIN"))
            if n!=1: raise RuntimeError("Code INSERT mismatch")
            db.commit()
            commit_time=datetime.now(timezone.utc).isoformat()
        except Exception:
            db.rollback()
            raise
        # Read after commit, compare content and ensure the authoritative Rule is unchanged.
        after=db.fetch_one("SELECT * FROM cm_common_code WHERE group_code=%s AND code=%s",(GROUP_CODE,RULE_CODE))
        after_group=db.fetch_one("SELECT * FROM cm_common_code_group WHERE group_code=%s",(GROUP_CODE,))
        after_rule=db.fetch_one("SELECT * FROM rl_rule WHERE rule_code=%s",(RULE_CODE,))
        ok=(after is not None and after_group is not None and after_rule==rule
            and after["status_code"]=="DRAFT" and json.loads(after["common_code_json"])==payload
            and after["common_code_description"]==rule["rule_description"]
            and (group is None or group==after_group))
        result={"success":ok,"commit_returned_successfully":True,"commit_observed_utc":commit_time,
                "plan_hash":plan_hash,"backup":evidence,"after_code":after,"after_group":after_group,
                "original_rule_preserved":after_rule==rule,"enforced":False}
        path=save("result",result,stamp)
        print(json.dumps({"success":ok,"group_code":GROUP_CODE,"code":RULE_CODE,"status_code":after["status_code"],
                          "enforced":False,"original_rule_preserved":after_rule==rule,
                          "post_commit_select_matches":ok,"evidence":path},ensure_ascii=False))
        if not ok: raise RuntimeError("Post-commit verification mismatch; inspect before retry")

if __name__=="__main__":
    main()
