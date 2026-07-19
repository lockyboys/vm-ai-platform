#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/data/vm_project}"
SQL_FILE="$PROJECT_DIR/sql/runtime/object_hierarchy_compatibility_20260719.sql"

set -a
source "$PROJECT_DIR/.env"
set +a

"$PROJECT_DIR/venv/bin/python" -m compileall -f \
    "$PROJECT_DIR/engine/identifier_engine.py"

MYSQL_PWD="$COMMON_MARIADB_PASSWORD" mariadb \
    --abort-source-on-error \
    --default-character-set=utf8mb4 \
    -h "$COMMON_MARIADB_HOST" \
    -P "$COMMON_MARIADB_PORT" \
    -u "$COMMON_MARIADB_USER" \
    < "$SQL_FILE"

echo "SUCCESS: L0-L5 compatibility migration completed."
