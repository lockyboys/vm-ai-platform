"""삼성화재 공시실 HTML/JS API 탐색 probe. 다운로드·DB 변경 없이 증거만 만든다."""
from __future__ import annotations
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

URLS = [
    "https://www.samsungfire.com/vh/page/VH.REIF0012.do",
    "https://m.samsungfire.com/vh/page/VH.HPIF0103.do",
]
UA = "SPS-SamsungFire-Probe/1.0"

def fetch(url: str) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, "replace"), response.geturl()

def main() -> None:
    evidence = {"urls": [], "script_urls": [], "candidate_lines": []}
    seen = set()
    for url in URLS:
        html, final_url = fetch(url)
        evidence["urls"].append({"requested": url, "final": final_url, "html_bytes": len(html)})
        for src in re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", html, re.I):
            script_url = urllib.parse.urljoin(final_url, src)
            if script_url in seen:
                continue
            seen.add(script_url)
            evidence["script_urls"].append(script_url)
            try:
                js, _ = fetch(script_url)
            except Exception as error:
                evidence["candidate_lines"].append({"script": script_url, "error": f"{type(error).__name__}: {error}"})
                continue
            for line in js.splitlines():
                if re.search(r"onSaleList|comSaleList|HPIF0103|REIF0012|약관|publication|download|pdf|api", line, re.I):
                    evidence["candidate_lines"].append({"script": script_url, "line": line[:1000]})
    print(json.dumps(evidence, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
