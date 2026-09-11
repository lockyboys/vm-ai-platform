#!/usr/bin/env bash
# Verify all eleven MariaDB payload backup tables without modifying any table.

set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
exec "${project_root}/venv/bin/python" -m harness.scripts.verify_storage_separation_mariadb_backups
