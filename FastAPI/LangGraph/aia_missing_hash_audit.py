"""AIA 제목 사본 중 이름이 달라진 PDF의 바이트 해시를 읽기 전용으로 대조한다."""
import hashlib
import json
from pathlib import Path

BASE = Path("/data/vm_project/outputs/insurance_docs/AIA")
LOG = BASE / "first_page_titles"
DEST = BASE / "first_page_named"

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    rows = []
    for log, key in (("copies.jsonl", "status"), ("recovery.jsonl", "copy_status")):
        with (LOG / log).open(encoding="utf-8") as stream:
            rows += [r for line in stream if (r := json.loads(line)).get(key) == "COPY_VERIFIED"]
    by_name = {r["filename"]: r for r in rows}
    files = {p.name: p for p in DEST.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"}
    missing = [r for r in rows if r["filename"] not in files]
    extra = [(name, path) for name, path in files.items() if name not in by_name]
    by_sha = {}
    for name, path in extra:
        by_sha.setdefault(digest(path), []).append(name)
    mappings = []
    for r in missing:
        original_hash = r.get("sha256")
        matches = by_sha.get(original_hash, [])
        mappings.append({"source": r["source"], "expected": r["filename"],
                         "renamed_to": matches, "original_hash_present": bool(original_hash)})
    print(json.dumps({"verified_records": len(rows), "current_named_pdf": len(files),
                      "missing_expected": len(missing), "extra_names": len(extra),
                      "hash_matched": sum(bool(m["renamed_to"]) for m in mappings),
                      "unmatched_extra": [name for name, p in extra if digest(p) not in {r.get("sha256") for r in missing}],
                      "mappings": mappings}, ensure_ascii=False))

if __name__ == "__main__":
    main()
