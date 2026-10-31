"""삼성화재 상품목록 API와 PDF 규칙 추출 probe."""
from __future__ import annotations
import json
import re
import urllib.request

JS_URL = "https://www.samsungfire.com/sfmi/ui/etcsv/info/productListHandler_new.js?v=20240124"
PAGE_URL = "https://www.samsungfire.com/vh/page/VH.REIF0012.do"
UA = "SPS-SamsungFire-API-Extractor/1.0"

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8", "replace")

def main() -> None:
    html = fetch(PAGE_URL)
    js = fetch(JS_URL)
    patterns = re.compile(r"ajax|url\\s*:|productcode|sellstart|gubun|publication/pdf|fileDownload|\.do|\.json|\.xml|\.php", re.I)
    result = {
        "page_bytes": len(html),
        "js_bytes": len(js),
        "pdf_rule_lines": [],
        "api_candidate_lines": [],
        "page_data_lines": [],
    }
    for line in js.splitlines():
        if "publication/pdf" in line or "fileDownload" in line:
            result["pdf_rule_lines"].append(line.strip()[:1200])
        if patterns.search(line) and len(result["api_candidate_lines"]) < 250:
            result["api_candidate_lines"].append(line.strip()[:1200])
    for line in html.splitlines():
        if re.search(r"product|onSale|comSale|api|\.do|\.json|\.xml", line, re.I):
            result["page_data_lines"].append(line.strip()[:1200])
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
