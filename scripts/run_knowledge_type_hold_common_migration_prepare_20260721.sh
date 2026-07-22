#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/data/vm_project}"
PATCH_FILE="sql/runtime/knowledge_type_hold_common_migration_prepare_20260721.sql"
HOLD_FILE="sql/runtime/knowledge_type_hold_migration_hold_registration_20260721.sql"

cd "${PROJECT_ROOT}"

for required_file in "${HOLD_FILE}" "${PATCH_FILE}"; do
  if [[ ! -f "${required_file}" ]]; then
    echo "ERROR: patch file not found: ${PROJECT_ROOT}/${required_file}" >&2
    exit 1
  fi
done

python tools/run_repository_data_type_patch_20260720.py "${HOLD_FILE}"
python tools/run_repository_data_type_patch_20260720.py "${PATCH_FILE}"
