"""AIA 제목 사본 검증 기록과 현 파일을 읽기 전용으로 대조한다."""
import json
import re
from pathlib import Path

BASE = Path("/data/vm_project/outputs/insurance_docs/AIA")
LOG = BASE / "first_page_titles"
DEST = BASE / "first_page_named"
PDF = BASE / "pdf"

def main():
    records = []
    for filename, field in (("copies.jsonl", "status"), ("recovery.jsonl", "copy_status")):
        with (LOG / filename).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row.get(field) == "COPY_VERIFIED":
                    records.append(row)
    named = {p.name: p for p in DEST.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"}
    expected = {r["filename"]: r for r in records}
    missing = []
    for row in records:
        filename = row["filename"]
        if filename in named:
            continue
        source = row["source"]
        stem = Path(source).stem
        suffix = "__" + stem + ".pdf"
        alternatives = [name for name in named if name.endswith(suffix)]
        source_path = PDF / source
        missing.append({"expected": filename, "source": source,
                        "source_present": source_path.is_file(),
                        "alternate_names": alternatives})
    extras = [name for name in named if name not in expected]
    print(json.dumps({
        "verified_records": len(records), "unique_expected": len(expected),
        "current_named_pdf": len(named), "exact_present": len(expected) - len(missing),
        "missing_count": len(missing), "missing": missing,
        "alternate_count": sum(bool(r["alternate_names"]) for r in missing),
        "source_present_count": sum(r["source_present"] for r in missing),
        "extra_named_count": len(extras),
        "extra_samples": extras[:10]
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
