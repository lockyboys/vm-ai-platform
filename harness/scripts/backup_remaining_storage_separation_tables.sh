#!/usr/bin/env bash
# Run the approved seven-table storage-separation backup from the project root.
# Preview first; add --apply only when writing a new immutable backup set.

set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
exec "${project_root}/venv/bin/python" \
  -m harness.scripts.backup_remaining_storage_separation_tables "$@"
