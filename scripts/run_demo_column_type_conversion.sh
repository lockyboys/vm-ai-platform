#!/usr/bin/env bash
# Run a TEMPORARY-table conversion demo, then rebuild and print the live read-only inventory.

set -euo pipefail

PROJECT_DIR="/data/vm_project"
PYTHON="${PROJECT_DIR}/venv/bin/python"
SQL_FILE="${PROJECT_DIR}/sql/runtime/demo_column_type_conversion_20260720.sql"
ENV_FILE="${PROJECT_DIR}/.env"

cd "${PROJECT_DIR}"

if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${ENV_FILE}"
    set +a
fi

for name in \
    COMMON_MARIADB_HOST \
    COMMON_MARIADB_PORT \
    COMMON_MARIADB_USER \
    COMMON_MARIADB_PASSWORD
do
    if [[ -z "${!name:-}" ]]; then
        echo "ERROR: ${name} is not set." >&2
        exit 1
    fi
done

echo "================================================================================"
echo "SPS Column Type Conversion Demo"
echo "================================================================================"
echo "Safety: TEMPORARY TABLE only. Production tables are not changed."
echo "--------------------------------------------------------------------------------"

MYSQL_PWD="${COMMON_MARIADB_PASSWORD}" \
mariadb \
    -h "${COMMON_MARIADB_HOST}" \
    -P "${COMMON_MARIADB_PORT}" \
    -u "${COMMON_MARIADB_USER}" \
    te_common \
    < "${SQL_FILE}"

echo "--------------------------------------------------------------------------------"
echo "Rebuild live read-only Repository inventory"
echo "--------------------------------------------------------------------------------"
"${PYTHON}" tools/analyze_repository_data_types.py

echo "================================================================================"
echo "SUCCESS: Demo completed and Repository inventory was rebuilt."
echo "No production table ALTER was executed."
echo "================================================================================"
