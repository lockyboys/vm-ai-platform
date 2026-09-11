#!/usr/bin/env bash
# Migrate all rows for approved STORAGE_SEPARATION_TARGET contracts.
set -euo pipefail

python -m harness.scripts.migrate_storage_separation_contracts "$@"
