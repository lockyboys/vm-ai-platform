"""삼성화재 공시실 상품분류 응답과 JS 호출 문맥 probe."""
from __future__ import annotations
import json
import re
import urllib.request

BASE = "https://www.samsungfire.com"
JS_URL = BASE + "/sfmi/ui/etcsv/info/productListHandler_new.js?v=20240124"
UA = "SPS-SamsungFire-Catalog-Probe/1.0"

def fetch(url: str) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8", "replace"), response.headers.get("Content-Type", "")

def context(lines: list[str], needle: str, radius: int = 8) -> list[str]:
    out = []
    for i, line in enumerate(lines):
        if needle.lower() in line.lower():
            out.extend(f"{j+1}: {lines[j].strip()[:1200]}" for j in range(max(0, i-radius), min(len(lines), i+radius+1)))
    return out[:120]

def main() -> None:
    js, js_type = fetch(JS_URL)
    endpoint = BASE + "/vh/page/VH.RPMY0133.do"
    data, data_type = fetch(endpoint)
    lines = js.splitlines()
    print(json.dumps({
        "js_content_type": js_type,
        "catalog_endpoint": endpoint,
        "catalog_content_type": data_type,
        "catalog_bytes": len(data),
        "catalog_head": data[:8000],
        "ajax_context": context(lines, "$.get("),
        "ajax_url_context": context(lines, "RPMY0133"),
        "product_request_context": context(lines, "searchProduct"),
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
