"""삼성화재 전체 버전 약관 차이 분석(읽기 전용, 네트워크 없음) — 2026-11-11 LuckyBoys 요청.

목적
  1) manifest에 없는데 디스크에 있는 PDF(추가 파일)가 무엇인지 분류한다.
  2) 받지 못한 8건(errors)의 상품명·코드·판매기간·오류를 정리한다.
방법
  - manifest documents의 경로 값(키 이름은 가정하지 않고 '.pdf'로 끝나는 문자열 값 전부)을 기준 목록으로 쓴다.
  - 추가 파일은 파일명 규칙 '<상품명>_<상품코드>_<판매시작일>_약관.pdf'로 쪼개
    (a) 같은 상품코드가 manifest에 있는지, (b) 같은 상품코드+판매시작일이 있는지로 분류한다.
주의: 파일을 쓰거나 지우지 않는다. 결과 JSON은 stdout과 outputs 아래 분석 파일 1개에만 쓴다.
"""
import json
import re
from collections import Counter
from pathlib import Path

from samsungfire_terms_pdf_collect_all_versions import MANIFEST_NAME, OUT

manifest = json.loads((OUT / MANIFEST_NAME).read_text(encoding="utf-8"))


def pdf_strings(value):
    """중첩 구조에서 '.pdf'로 끝나는 문자열을 모두 뽑는다(키 이름 비의존)."""
    if isinstance(value, str):
        return [value] if value.lower().endswith(".pdf") else []
    if isinstance(value, dict):
        return [s for v in value.values() for s in pdf_strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in pdf_strings(v)]
    return []


manifest_names = {Path(p).name for p in pdf_strings(manifest.get("documents", []))}
disk_names = {p.name for p in OUT.glob("*.pdf")}
extra = sorted(disk_names - manifest_names)
missing_on_disk = sorted(manifest_names - disk_names)

NAME_RE = re.compile(r"^(?P<name>.+)_(?P<code>[^_]+)_(?P<start>[^_]+)_약관\.pdf$")


def split(name):
    m = NAME_RE.match(name)
    return (m["code"], m["start"]) if m else (None, None)


manifest_codes = Counter(split(n)[0] for n in manifest_names)
manifest_keys = {split(n) for n in manifest_names}
groups = {"same_code_other_start": [], "code_not_in_manifest": [], "same_code_same_start": [], "name_pattern_mismatch": []}
for n in extra:
    code, start = split(n)
    if code is None:
        groups["name_pattern_mismatch"].append(n)
    elif (code, start) in manifest_keys:
        groups["same_code_same_start"].append(n)      # 같은 버전인데 상품명 표기만 다른 경우
    elif code in manifest_codes:
        groups["same_code_other_start"].append(n)     # 같은 상품의 다른 판매시작일(현 카탈로그에 없는 버전)
    else:
        groups["code_not_in_manifest"].append(n)      # 현 카탈로그에 없는 상품코드

result = {
    "manifest_documents": len(manifest.get("documents", [])),
    "manifest_pdf_names": len(manifest_names),
    "disk_pdf_files": len(disk_names),
    "extra_on_disk": len(extra),
    "missing_on_disk": len(missing_on_disk),
    "extra_groups_count": {k: len(v) for k, v in groups.items()},
    "extra_groups_sample": {k: v[:10] for k, v in groups.items()},
    "errors": manifest.get("errors", []),
}
out_file = Path("/data/vm_project/outputs/insurance_docs/samsungfire_terms_gap_analysis_20261111.json")
out_file.write_text(json.dumps({**result, "extra_groups": groups, "missing_on_disk_list": missing_on_disk},
                               ensure_ascii=False, indent=2), encoding="utf-8")
result["full_report"] = str(out_file)
print(json.dumps(result, ensure_ascii=False, indent=2))
