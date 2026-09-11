#!/usr/bin/env bash
# Read-only gate: confirms MongoDB migration before any original field is dropped.
set -euo pipefail
python -m harness.scripts.verify_storage_separation_migrations "$@"
