#!/usr/bin/env bash
# Delete only the seven JSON logical backups made by backup_remaining_storage_separation_tables.sh.

set -Eeuo pipefail

apply=false
if [[ "${1:-}" == "--apply" ]]; then
  apply=true
elif [[ $# -ne 0 ]]; then
  echo "Usage: bash harness/scripts/delete_seven_logical_backups_20260902_02.sh [--apply]" >&2
  exit 2
fi

backup_root="/data/sps-harness-runtime/backups/mariadb/common"
targets=(
  "${backup_root}/cm_verified_sql_query__before_storage_separation_backup_20260902_02__20260902T123345+0000.json"
  "${backup_root}/model_history__before_storage_separation_backup_20260902_02__20260902T123345+0000.json"
  "${backup_root}/cm_repository__before_storage_separation_backup_20260902_02__20260902T123345+0000.json"
  "${backup_root}/cm_storage_repository__before_storage_separation_backup_20260902_02__20260902T123345+0000.json"
  "${backup_root}/cron_logs__before_storage_separation_backup_20260902_02__20260902T123345+0000.json"
  "${backup_root}/cm_code_inspection_result__before_storage_separation_backup_20260902_02__20260902T123345+0000.json"
  "${backup_root}/pipeline_results__before_storage_separation_backup_20260902_02__20260902T123346+0000.json"
)

for target in "${targets[@]}"; do
  [[ -f "${target}" ]] || { echo "Missing target: ${target}" >&2; exit 1; }
done

if [[ "${apply}" != true ]]; then
  printf 'Dry-run: 7 explicit JSON backup files. Re-run with --apply.\n'
  printf '%s\n' "${targets[@]}"
  exit 0
fi

for target in "${targets[@]}"; do
  rm -- "${target}"
done
echo "Deleted 7 JSON logical backup files."
