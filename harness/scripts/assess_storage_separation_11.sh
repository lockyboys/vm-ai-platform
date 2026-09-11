#!/usr/bin/env bash
# Read every one of the 11 separation targets without changing data.
set -euo pipefail
python -m harness.scripts.assess_storage_separation_11 "$@"
