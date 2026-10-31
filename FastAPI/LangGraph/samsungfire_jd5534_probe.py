from Agent_Import_PFDs.samsungfire_terms_downloader import catalog
import json
rows = catalog(True)
print(json.dumps([r for r in rows if r.get("product_code") == "JD5534"], ensure_ascii=False, indent=2))
