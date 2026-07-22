#!/usr/bin/env bash
set -euo pipefail

cd /data/vm_project
mkdir -p outputs/logs outputs/reports/common_code_complete_census_20260722
timestamp="$(date +%Y%m%d_%H%M%S)"
log_path="outputs/logs/common_code_complete_census_${timestamp}.log"

{
  echo '===== 1. COMPLETE 63/421 ROW AUDIT ====='
  python tools/audit_common_code_repository_20260721.py \
    --output-dir outputs/reports/common_code_complete_census_20260722 \
    --basename common_code_all_rows

  echo '===== 2. ALL REPOSITORY CODE-COLUMN IMPACT AUDIT ====='
  python tools/analyze_repository_common_code_links.py \
    --output-dir outputs/reports/common_code_complete_census_20260722 \
    --basename common_code_all_references

  python - <<'PY'
import json
from collections import Counter
from pathlib import Path

root = Path('outputs/reports/common_code_complete_census_20260722')
audit = json.loads((root / 'common_code_all_rows.json').read_text(encoding='utf-8'))
groups = audit['groups']
codes = audit['codes']
if len(groups) != 63 or len(codes) != 421:
    raise SystemExit(f'CARDINALITY_FAIL groups={len(groups)} codes={len(codes)}')

allowed = {'CREATE_MAINTAIN','MODIFY','DISPOSAL_CANDIDATE','DISPOSAL_IN_PROGRESS','DISPOSED','PRESERVE'}
bad_group_lifecycle = [r['group_code'] for r in groups if r.get('lifecycle_status_code') not in allowed]
bad_code_lifecycle = [[r['group_code'], r['code']] for r in codes if r.get('lifecycle_status_code') not in allowed]
current_group = Counter(r.get('lifecycle_status_code') for r in groups)
current_code = Counter(r.get('lifecycle_status_code') for r in codes)

clean_modify_groups = sorted(
    r['group_code'] for r in groups
    if r.get('lifecycle_status_code') == 'MODIFY'
    and not any(i['group_code'] == r['group_code'] for i in audit['group_issues'])
)
issue_keys = {(r['group_code'], r['code']) for r in audit['code_issues']}
clean_modify_codes = sorted(
    [r['group_code'], r['code']] for r in codes
    if r.get('lifecycle_status_code') == 'MODIFY'
    and (r['group_code'], r['code']) not in issue_keys
)
result = {
    'scope': {'groups': len(groups), 'codes': len(codes)},
    'quality_summary': audit['summary'],
    'current_group_lifecycle': dict(current_group),
    'current_code_lifecycle': dict(current_code),
    'bad_group_lifecycle': bad_group_lifecycle,
    'bad_code_lifecycle': bad_code_lifecycle,
    'clean_but_still_modify_groups': clean_modify_groups,
    'clean_but_still_modify_codes': clean_modify_codes,
}
(root / 'lifecycle_reclassification_findings.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
)
print(json.dumps(result, ensure_ascii=False, indent=2))
PY
} 2>&1 | tee "$log_path"

echo 'COMPLETE_CENSUS_SUCCESS'
echo "LOG_PATH=$log_path"