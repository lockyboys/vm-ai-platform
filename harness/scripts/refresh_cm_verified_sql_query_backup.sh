#!/usr/bin/env bash
# Preview first. Add --apply to atomically refresh only cm_verified_sql_query backup.

set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
exec "${project_root}/venv/bin/python" -m harness.scripts.refresh_cm_verified_sql_query_backup "$@"
