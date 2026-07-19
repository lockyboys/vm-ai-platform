#!/usr/bin/env bash
# Register column standards and rebuild the read-only Repository inventory.

set -euo pipefail

PROJECT_DIR="/data/vm_project"
PYTHON="${PROJECT_DIR}/venv/bin/python"
ENV_FILE="${PROJECT_DIR}/.env"

if [[ ! -d "${PROJECT_DIR}" ]]; then
    echo "ERROR: Project directory was not found: ${PROJECT_DIR}" >&2
    exit 1
fi

if [[ ! -x "${PYTHON}" ]]; then
    echo "ERROR: Project Python was not found: ${PYTHON}" >&2
    exit 1
fi

cd "${PROJECT_DIR}"

if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${ENV_FILE}"
    set +a
fi

echo "================================================================================"
echo "SPS Column Metadata Maintenance"
echo "================================================================================"
echo "[1/3] Upsert 23 required suffix standards"
"${PYTHON}" tools/upsert_column_suffix_metadata_20260719.py

echo "[2/3] Upsert exact, compound-suffix, suffix, prefix, and root rules"
"${PYTHON}" tools/upsert_column_semantic_metadata_20260719.py

echo "[3/3] Rebuild read-only Repository data type inventory"
"${PYTHON}" tools/analyze_repository_data_types.py

echo "================================================================================"
echo "SUCCESS: Metadata standards were registered and the inventory was rebuilt."
echo "No physical table ALTER was executed."
echo "Reports: ${PROJECT_DIR}/outputs/reports/repository_data_type_inventory_20260719.json"
echo "         ${PROJECT_DIR}/outputs/reports/repository_data_type_inventory_20260719.csv"
echo "         ${PROJECT_DIR}/outputs/reports/repository_data_type_inventory_20260719_mismatch.csv"
echo "================================================================================"
