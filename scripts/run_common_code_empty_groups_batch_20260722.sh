#!/usr/bin/env bash
set -euo pipefail

SQL_FILE="/data/vm_project/sql/runtime/common_code_empty_groups_batch_20260722.sql"
LOG_DIR="/data/vm_project/outputs/logs"
RUN_DT="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/common_code_empty_groups_batch_${RUN_DT}.log"

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

if [[ ! -f "${SQL_FILE}" ]]; then
  echo "ERROR: SQL file not found: ${SQL_FILE}" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}"

MYSQL_PWD="${COMMON_MARIADB_PASSWORD}" mariadb   --host="${COMMON_MARIADB_HOST}"   --port="${COMMON_MARIADB_PORT}"   --user="${COMMON_MARIADB_USER}"   --database="${COMMON_MARIADB_DATABASE}"   --show-warnings   --verbose   < "${SQL_FILE}" 2>&1 | tee "${LOG_FILE}"

echo "SUCCESS: batch completed"
echo "LOG_FILE=${LOG_FILE}"
