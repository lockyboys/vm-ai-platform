"""Record four document-only payload policies as DRAFT Rules.
Never updates existing rules, registers actions, or changes runtime writers.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from common.database import CommonDatabase

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "harness/memory/payload_policy_rule_manifest_20261025.json"
BASE = ROOT / "harness/memory/payload_policy_registration"
FIELDS = ("rule_code","rule_name","rule_type_code","status_code","version_num","sort_no","rule_description","remark")

def dump(path, value):
    """Preserve each preflight/result immutably; never replace earlier evidence."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)

def main():
    """Validate a reviewed manifest, optionally insert four Rules, then SELECT."""
    request = json.loads(sys.stdin.read() or "{}")
    mode = request.get("mode", "plan")
    if mode not in ("plan", "apply"):
        raise ValueError("mode must be plan or apply")
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))["rows"]
    document = ROOT / "harness/instructions/SPS_HARNESS_STANDARD.md"
    actual_hash = hashlib.sha256(document.read_bytes()).hexdigest()
    for row in rows:
        policy = json.loads(row["remark"])
        if policy["source_sha256"] != actual_hash:
            raise ValueError("Source policy changed; regenerate/review the manifest")
        if row["status_code"] != "DRAFT" or policy["enforced"] is not False:
            raise ValueError("This registration must remain non-enforced DRAFT")
        if len(row["rule_description"]) > 2000 or len(row["remark"]) > 2000:
            raise ValueError("Rule text exceeds documented field limit")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    result = {"mode":mode, "enforced":False, "source_sha256":actual_hash,
              "manifest_sha256":hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}
    with CommonDatabase(database_role="COMMON") as db:
        # Read live table and every field COMMENT before any business write.
        schema = db.fetch_one("SHOW CREATE TABLE rl_rule")
        columns = db.fetch_all(
            "SELECT column_name,column_comment FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name=%s", (db.database_name,"rl_rule"))
        if any(not col["column_comment"] for col in columns):
            raise ValueError("Missing rl_rule column COMMENT")
        if not schema or "COMMENT=" not in schema["Create Table"]:
            raise ValueError("Missing table COMMENT")
        for group, code in (("RULE_TYPE","LIFECYCLE"),("STATUS_CODE","DRAFT")):
            if not db.fetch_one(
                "SELECT code FROM cm_common_code WHERE group_code=%s AND code=%s "
                "AND status_code=%s AND deleted_dt IS NULL", (group,code,"ACTIVE")):
                raise ValueError("Required common code is not active")
        previous = db.fetch_all("SELECT * FROM rl_rule ORDER BY rule_id")
        wanted_codes = {r["rule_code"] for r in rows}
        if any(r["rule_code"] in wanted_codes for r in previous):
            raise ValueError("A policy already exists; inspect saved outcome instead of overwriting")
        result["existing_rule_count"] = len(previous)
        result["planned_codes"] = sorted(wanted_codes)
        result["schema"] = schema
        result["column_comments"] = columns
        if mode == "plan":
            result["writes"] = 0
            result["allocation_required"] = 4
            path = Path(str(BASE) + "_plan_" + stamp + ".json")
            dump(path, {**result, "before_rows":previous, "manifest":rows})
            print(json.dumps({"success":True,"dry_run":True,"evidence":str(path),
                              "planned_codes":result["planned_codes"]},ensure_ascii=False))
            return
        # The caller supplies four Identifier Engine IDs reviewed for rl_rule.rule_id.
        ids = request.get("rule_ids", [])
        if len(ids) != 4 or len(set(ids)) != 4 or any(not isinstance(x,str) or not x or len(x)>99 for x in ids):
            raise ValueError("Four unique engine-generated rule_ids are required")
        backup = Path(str(BASE) + "_before_" + stamp + ".json")
        dump(backup, {"before_rows":previous,"schema":schema,"column_comments":columns,
                      "manifest":rows,"rule_ids":ids,"source_sha256":actual_hash})
        result["backup"] = str(backup)
        db.begin()
        try:
            # Lock and compare to the preserved snapshot; stop on concurrent edits.
            locked = db.fetch_all("SELECT * FROM rl_rule ORDER BY rule_id FOR UPDATE")
            if locked != previous:
                raise ValueError("Existing rules changed after snapshot")
            for identifier, row in zip(ids, rows):
                count = db.execute(
                    "INSERT INTO rl_rule (rule_id,rule_code,rule_name,rule_type_code,"
                    "status_code,version_num,sort_no,rule_description,remark,"
                    "created_by,program_id,client_ip) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (identifier, *(row[field] for field in FIELDS),
                     "CODEX","PAYLOAD_POLICY_RECORD_20261025","127.0.0.1"))
                if count != 1:
                    raise RuntimeError("INSERT affected row count mismatch")
            inserted = db.fetch_all(
                "SELECT * FROM rl_rule WHERE rule_id IN (%s,%s,%s,%s) ORDER BY sort_no",
                tuple(ids))
            if len(inserted) != 4 or any(
                got["rule_id"] != identifier or any(got[f] != row[f] for f in FIELDS)
                for got, identifier, row in zip(inserted, ids, rows)):
                raise RuntimeError("Pre-commit SELECT mismatch")
            db.commit()
            result["commit_returned_successfully"] = True
            result["commit_observed_utc"] = datetime.now(timezone.utc).isoformat()
        except Exception:
            db.rollback()
            raise
        # A new read after commit proves visibility; preserve all original rows exactly.
        after = db.fetch_all("SELECT * FROM rl_rule ORDER BY rule_id")
        by_id = {r["rule_id"]:r for r in after}
        preserved = all(by_id.get(r["rule_id"]) == r for r in previous)
        stored = [by_id.get(x) for x in ids]
        matches = all(got and all(got[f]==row[f] for f in FIELDS) for got,row in zip(stored,rows))
        result.update({"existing_rows_preserved":preserved,
                       "registered_rows":stored,"post_commit_select_matches":matches,
                       "before_count":len(previous),"after_count":len(after)})
        evidence = Path(str(BASE) + "_result_" + stamp + ".json")
        dump(evidence, result)
        if not preserved or not matches:
            raise RuntimeError("Post-commit verification failed; inspect evidence without retry")
        print(json.dumps({"success":True,"registered":4,"status":"DRAFT","enforced":False,
                          "existing_rows_preserved":preserved,"post_commit_select_matches":matches,
                          "rows":[{"rule_id":r["rule_id"],"rule_code":r["rule_code"]} for r in stored],
                          "evidence":str(evidence),"backup":str(backup)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
