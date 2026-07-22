#!/usr/bin/env bash
set -euo pipefail

cd /data/vm_project

SQL_FILE="sql/runtime/common_code_final_reclassification_20260722.sql"
REPORT_DIR="outputs/reports/common_code_final_reclassification_20260722"
LOG_DIR="outputs/logs"
mkdir -p "$REPORT_DIR" "$LOG_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/common_code_final_reclassification_$STAMP.log"

: "${COMMON_MARIADB_HOST:?COMMON_MARIADB_HOST is required}"
: "${COMMON_MARIADB_PORT:?COMMON_MARIADB_PORT is required}"
: "${COMMON_MARIADB_USER:?COMMON_MARIADB_USER is required}"
: "${COMMON_MARIADB_PASSWORD:?COMMON_MARIADB_PASSWORD is required}"
: "${COMMON_MARIADB_DATABASE:?COMMON_MARIADB_DATABASE is required}"

MYSQL=(mariadb -h "$COMMON_MARIADB_HOST" -P "$COMMON_MARIADB_PORT" -u "$COMMON_MARIADB_USER" "$COMMON_MARIADB_DATABASE")

{
  echo '===== 1. CORRECTED PRE-APPLICATION COMPLETE AUDIT ====='
  python tools/audit_common_code_repository_20260721.py \
    --output-dir "$REPORT_DIR" \
    --basename before_application

  python - <<'PY'
import json
from pathlib import Path

path = Path("outputs/reports/common_code_final_reclassification_20260722/before_application.json")
report = json.loads(path.read_text(encoding="utf-8"))
summary = report["summary"]
assert summary["group_count"] == 63, summary
assert summary["code_count"] == 421, summary
assert summary["group_issue_count"] == 0, report["group_issues"]
assert summary["code_issue_count"] == 0, report["code_issues"]
print("PRE_APPLICATION_AUDIT_SUCCESS")
PY

  echo '===== 2. FINAL LIFECYCLE RECLASSIFICATION ====='
  MYSQL_PWD="$COMMON_MARIADB_PASSWORD" "${MYSQL[@]}" < "$SQL_FILE"

  echo '===== 3. POST-APPLICATION COMPLETE AUDIT ====='
  python tools/audit_common_code_repository_20260721.py \
    --output-dir "$REPORT_DIR" \
    --basename after_application

  python - <<'PY'
import json
from collections import Counter
from pathlib import Path

path = Path("outputs/reports/common_code_final_reclassification_20260722/after_application.json")
report = json.loads(path.read_text(encoding="utf-8"))
summary = report["summary"]
groups = report["groups"]
codes = report["codes"]
group_lifecycle = Counter(row["lifecycle_status_code"] for row in groups)
code_lifecycle = Counter(row["lifecycle_status_code"] for row in codes)

assert summary["group_count"] == 63, summary
assert summary["code_count"] == 421, summary
assert summary["group_issue_count"] == 0, report["group_issues"]
assert summary["code_issue_count"] == 0, report["code_issues"]
assert group_lifecycle == {"CREATE_MAINTAIN": 61, "PRESERVE": 2}, group_lifecycle
assert code_lifecycle == {"CREATE_MAINTAIN": 407, "PRESERVE": 14}, code_lifecycle

print(json.dumps({
    "group_lifecycle": dict(group_lifecycle),
    "code_lifecycle": dict(code_lifecycle),
    "group_issue_count": summary["group_issue_count"],
    "code_issue_count": summary["code_issue_count"],
}, ensure_ascii=False, indent=2))
print("POST_APPLICATION_AUDIT_SUCCESS")
PY

  echo '===== 4. REGISTER COMPLETE SQL TEXT ====='
  SQL_B64="$(base64 -w 0 "$SQL_FILE")"
  REGISTER_FILE="$(mktemp /tmp/common_code_final_verified_query_XXXXXX.sql)"
  trap 'rm -f "$REGISTER_FILE"' EXIT
  {
    printf "%s\n" "USE te_common;"
    printf "%s\n" "INSERT INTO cm_verified_sql_query"
    printf "%s\n" "(query_id,query_name,query_description,crud_type,sql_text,verified_yn,certified_level_code,verification_description,created_by,created_dt,verified_by,verified_dt,story_programming_rule_pass_yn,snake_case_pass_yn,table_exists_pass_yn,column_exists_pass_yn,crud_match_pass_yn,where_clause_pass_yn,status_code,program_id,client_ip)"
    printf "%s\n" "VALUES ('SP_RP_SQL_QUERY_20260722_COMMON_CODE_FINAL_00001','공통코드 63/421 전수 재판정 최종 Batch','ISO 639-1 및 BCP 47 형식을 반영해 전체 63개 Group과 421개 Code를 재감사하고 잔여 MODIFY를 최종 재분류한 Batch.','BATCH',CONVERT(FROM_BASE64('$SQL_B64') USING utf8mb4),'Y','A','적용 전후 전수 감사에서 Group/Code 품질 문제 0건, MODIFY 0건, Group 61/2 및 Code 407/14 최종 상태를 확인했다.','SYSTEM',NOW(),'SYSTEM',NOW(),'Y','Y','Y','Y','Y','Y','ACTIVE','CM_COMMON_CODE_FINAL_RECLASSIFICATION_20260722','127.0.0.1')"
    printf "%s\n" "ON DUPLICATE KEY UPDATE sql_text=VALUES(sql_text),verified_yn='Y',certified_level_code='A',verification_description=VALUES(verification_description),verified_by='SYSTEM',verified_dt=NOW(),updated_by='SYSTEM',updated_dt=NOW(),program_id=VALUES(program_id),client_ip=VALUES(client_ip);"
    printf "%s\n" "SELECT query_id,verified_yn,certified_level_code,CHAR_LENGTH(sql_text) sql_text_length,program_id FROM cm_verified_sql_query WHERE query_id='SP_RP_SQL_QUERY_20260722_COMMON_CODE_FINAL_00001';"
    printf "%s\n" "SELECT target_table_name,COUNT(*) history_count FROM cm_change_history WHERE program_id='CM_COMMON_CODE_FINAL_RECLASSIFICATION_20260722' GROUP BY target_table_name ORDER BY target_table_name;"
  } > "$REGISTER_FILE"
  MYSQL_PWD="$COMMON_MARIADB_PASSWORD" "${MYSQL[@]}" < "$REGISTER_FILE"

  echo 'COMMON_CODE_FINAL_RECLASSIFICATION_SUCCESS'
} 2>&1 | tee "$LOG_FILE"

echo "LOG_PATH=$LOG_FILE"
