"""삼성화재 수집 manifest 검증."""
import json
p = "/data/vm_project/outputs/insurance_docs/samsung_fire_terms/samsungfire_terms_downloaded_manifest.json"
m = json.load(open(p, encoding="utf-8"))
print({"catalog_count": m["catalog_count"], "downloaded_count": m["downloaded_count"], "error_count": m["error_count"], "errors": m["errors"]})
