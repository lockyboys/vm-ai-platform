"""Read-only preflight for recording a non-enforced SPS payload policy.
No source/audit rows, sequences, or Repository records are changed.
"""
import json
from pathlib import Path
from common.database import CommonDatabase
def main():
    result = {}
    with CommonDatabase(database_role="COMMON") as common:
        result["codes"] = common.fetch_all(
            "SELECT group_code,code,code_name,status_code FROM cm_common_code "
            "WHERE group_code IN (%s,%s,%s,%s,%s,%s) AND deleted_dt IS NULL",
            ("RULE_TYPE","STATUS_CODE","SPS_METADATA_TARGET","SPS_METADATA_TYPE","METADATA_VALUE_TYPE","ACTION_TYPE"))
        result["rules"] = common.fetch_all(
            "SELECT * FROM rl_rule WHERE rule_code LIKE %s OR rule_code LIKE %s",
            ("%PAYLOAD%","%STORAGE%"))
    with CommonDatabase(database_role="STORY") as story:
        result["objects"] = story.fetch_all(
            "SELECT * FROM sp_object WHERE deleted_dt IS NULL AND "
            "(object_code IN (%s,%s) OR object_name LIKE %s OR object_name LIKE %s OR object_id=%s)",
            ("RL_RULE","METADATA","%sp_metadata","%cm_verified_sql_query","SP_RP_OBJECT_20260714_003504_00007"))
        result["existing_metadata"] = story.fetch_all(
            "SELECT * FROM sp_metadata WHERE metadata_key LIKE %s OR metadata_key LIKE %s",
            ("%payload%","%PAYLOAD%"))
    path = Path("harness/memory/payload_policy_record_preflight_20261025.json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, default=str))
if __name__ == "__main__":
    main()
