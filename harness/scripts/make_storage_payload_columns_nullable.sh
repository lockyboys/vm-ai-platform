#!/usr/bin/env bash
# Remove NOT NULL constraints from the three storage-separation payload columns.
set -euo pipefail

python -m harness.scripts.make_storage_payload_columns_nullable "$@"
