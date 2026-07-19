#!/usr/bin/env bash
# SPS Repository Knowledge initial batch runner
# Knowledge records only: this runner performs no DROP, ALTER, or RENAME.

set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/data/vm_project}"
SQL_FILE="${SQL_FILE:-$PROJECT_DIR/sql/runtime/repository_knowledge_batch_20260719.sql}"

required_variables=(
    COMMON_MARIADB_HOST
    COMMON_MARIADB_PORT
    COMMON_MARIADB_USER
    COMMON_MARIADB_PASSWORD
)

for variable_name in "${required_variables[@]}"; do
    if [[ -z "${!variable_name:-}" ]]; then
        echo "ERROR: $variable_name is not set." >&2
        exit 1
    fi
done

if [[ ! -f "$SQL_FILE" ]]; then
    echo "ERROR: SQL file was not found: $SQL_FILE" >&2
    exit 1
fi

echo "SPS Repository Knowledge batch"
echo "SQL: $SQL_FILE"
echo "DB : $COMMON_MARIADB_HOST:$COMMON_MARIADB_PORT"

MYSQL_PWD="$COMMON_MARIADB_PASSWORD" mariadb \
    --abort-source-on-error \
    --default-character-set=utf8mb4 \
    -h "$COMMON_MARIADB_HOST" \
    -P "$COMMON_MARIADB_PORT" \
    -u "$COMMON_MARIADB_USER" \
    < "$SQL_FILE"

echo "SUCCESS: Knowledge Object and Relationship batch committed."