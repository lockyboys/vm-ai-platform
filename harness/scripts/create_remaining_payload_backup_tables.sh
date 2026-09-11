#!/usr/bin/env bash
# Preview first. Add --apply to create MariaDB backup tables.

set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
exec "${project_root}/venv/bin/python" -m harness.scripts.create_remaining_payload_backup_tables "$@"
