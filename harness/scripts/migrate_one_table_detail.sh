#!/usr/bin/env bash
# Run the approved single-record storage migration from the Harness directory.
set -euo pipefail

python -m harness.scripts.migrate_one_table_detail "$@"
