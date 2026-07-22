#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data/vm_project"
SQL_FILE="${PROJECT_ROOT}/sql/runtime/common_code_history_verified_query_20260722.sql"
LOG_DIR="${PROJECT_ROOT}/outputs/logs"
REPORT_DIR="${PROJECT_ROOT}/outputs/reports"
RUN_DT="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/common_code_history_verified_query_${RUN_DT}.log"
AUDIT_LOG="${LOG_DIR}/common_code_full_reaudit_${RUN_DT}.log"
AUDIT_BASENAME="common_code_full_audit_20260722_after_empty_group_batch"

required_vars=(
  COMMON_MARIADB_HOST
  COMMON_MARIADB_PORT
  COMMON_MARIADB_USER
  COMMON_MARIADB_PASSWORD
  COMMON_MARIADB_DATABASE
)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "ERROR: required environment variable is missing: ${var_name}" >&2
    exit 1
  fi
done

mkdir -p "${LOG_DIR}" "${REPORT_DIR}"
cd "${PROJECT_ROOT}"

MYSQL_PWD="${COMMON_MARIADB_PASSWORD}" mariadb   --host="${COMMON_MARIADB_HOST}"   --port="${COMMON_MARIADB_PORT}"   --user="${COMMON_MARIADB_USER}"   --database="${COMMON_MARIADB_DATABASE}"   --show-warnings   --verbose   < "${SQL_FILE}" 2>&1 | tee "${LOG_FILE}"

python tools/audit_common_code_repository_20260721.py   --output-dir "${REPORT_DIR}"   --basename "${AUDIT_BASENAME}" 2>&1 | tee "${AUDIT_LOG}"

python - <<'PY'
import json
from pathlib import Path

path = Path("/data/vm_project/outputs/reports/common_code_full_audit_20260722_after_empty_group_batch.json")
report = json.loads(path.read_text(encoding="utf-8"))
summary = report["summary"]

if summary["group_count"] != 62:
    raise SystemExit(f"FAIL: expected 62 groups, got {summary['group_count']}")
if summary["code_count"] != 415:
    raise SystemExit(f"FAIL: expected 415 codes, got {summary['code_count']}")
if summary["empty_group_count"] != 0:
    raise SystemExit(f"FAIL: expected zero empty groups, got {summary['empty_group_count']}")

print("PASS: 62 groups")
print("PASS: 415 codes")
print("PASS: zero empty groups")
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY

echo "SUCCESS: History, Verified SQL Query, and full re-audit completed"
echo "HISTORY_VERIFIED_QUERY_LOG=${LOG_FILE}"
echo "AUDIT_LOG=${AUDIT_LOG}"
echo "AUDIT_JSON=${REPORT_DIR}/${AUDIT_BASENAME}.json"
echo "AUDIT_CSV=${REPORT_DIR}/${AUDIT_BASENAME}_group_summary.csv"
