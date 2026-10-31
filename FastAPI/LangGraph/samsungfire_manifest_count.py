import json
from pathlib import Path
p = Path("/data/vm_project/outputs/insurance_docs/samsung_fire_terms/samsungfire_terms_downloaded_manifest.json")
m = json.loads(p.read_text(encoding="utf-8"))
docs = m.get("documents", [])
print(json.dumps({
    "catalog_count": m.get("catalog_count"),
    "downloaded_count": m.get("downloaded_count"),
    "reused_count": sum(1 for d in docs if d.get("reused") is True),
    "new_download_count": sum(1 for d in docs if d.get("reused") is False),
    "error_count": m.get("error_count"),
}, ensure_ascii=False))
