"""삼성화재 전체 버전 약관 재검증(읽기 전용, 네트워크 없음) — 2026-11-10 LuckyBoys 요청.

목적: manifest가 말하는 수와 디스크의 실제 PDF 수(유효 PDF: %PDF- 헤더 + %%EOF)를 대조한다.
주의: 파일을 쓰거나 지우지 않는다. 카탈로그를 다시 받지 않는다(manifest 기록값 사용).
"""
import json
from pathlib import Path

from samsungfire_terms_pdf_collect_all_versions import MANIFEST_NAME, OUT, is_valid_pdf

manifest_path = OUT / MANIFEST_NAME
manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}

# manifest 최상위의 숫자 값만 요약(구조가 바뀌어도 깨지지 않게 키 이름을 가정하지 않음)
summary = {k: v for k, v in manifest.items() if isinstance(v, (int, float, str)) and not isinstance(v, bool)}
list_sizes = {k: len(v) for k, v in manifest.items() if isinstance(v, (list, dict))}

pdfs = sorted(OUT.glob("*.pdf"))
valid = [p for p in pdfs if is_valid_pdf(p)]
print(json.dumps({
    "output_dir": str(OUT),
    "manifest_exists": manifest_path.is_file(),
    "manifest_scalars": summary,
    "manifest_list_sizes": list_sizes,
    "pdf_files_on_disk": len(pdfs),
    "valid_pdf_files": len(valid),
    "invalid_pdf_files": [p.name for p in pdfs if p not in valid][:20],
    "total_bytes": sum(p.stat().st_size for p in valid),
}, ensure_ascii=False, indent=2))
