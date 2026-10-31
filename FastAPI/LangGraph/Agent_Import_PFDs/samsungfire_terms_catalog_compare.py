"""삼성화재 현행/판매종료 약관 카탈로그 수 비교."""
import json
from samsungfire_terms_downloader import catalog
print(json.dumps({
    "active_terms": len(catalog(False)),
    "including_stopped_terms": len(catalog(True)),
}, ensure_ascii=False))
