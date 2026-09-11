#!/usr/bin/env bash
# Drops payload columns only after backup and NULL-value safety checks pass.
set -euo pipefail
python -m harness.scripts.drop_storage_separation_payload_columns "$@"
