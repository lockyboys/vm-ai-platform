"""공개 공시 사이트 구조 탐색기(읽기 전용, 사이트 비종속).

목적: 새 보험사 수집 프로파일을 만들기 전에 목록 페이지와 그 페이지가 불러오는
JS 파일에서 AJAX(.do/.json) 엔드포인트, 다운로드 함수, 폼 파라미터 후보를 자동 추출한다.
- 입력(stdin JSON): {"url": "...", "max_scripts": 10, "keywords": ["약관", ...],
                    "method": "GET|POST", "data": {...}, "raw_limit": 0, "raw_offset": 0}
- 출력(stdout JSON): 페이지 상태, 스크립트 목록, 엔드포인트 후보, 키워드 주변 발췌
- 파일을 쓰지 않는다. 공개 목록 조회용 GET/POST만 보낸다(수집기 본체 실행 전 dry-run 성격).
"""

from __future__ import annotations

import json
import re
import sys
from urllib.parse import urljoin

import requests

# 엔드포인트·다운로드 함수 후보를 찾는 정규식(사이트 이름을 하드코딩하지 않는다)
_ENDPOINT = re.compile(r"""["']([^"'\s]*?\.(?:do|json|ajax)(?:\?[^"'\s]*)?)["']""")
_SCRIPT_SRC = re.compile(r"""<script[^>]+src=["']([^"']+)["']""", re.I)
_FUNC_CALL = re.compile(r"""(?:onclick|href)=["'](?:javascript:)?\s*([A-Za-z_$][\w$.]*\([^"']{0,200}\))""", re.I)
_DOWNLOAD_HINT = re.compile(r"""[^\n]{0,160}(?:download|Down|FileDown|filePath|fileName|\.pdf)[^\n]{0,160}""")


def _excerpts(text: str, keywords: list[str], width: int = 160, limit: int = 15) -> list[str]:
    """키워드 주변 문자열을 최대 limit개 발췌한다."""
    found: list[str] = []
    for keyword in keywords:
        for match in re.finditer(re.escape(keyword), text):
            start, end = max(0, match.start() - width), match.end() + width
            found.append(re.sub(r"\s+", " ", text[start:end]))
            if len(found) >= limit:
                return found
    return found


def main() -> None:
    request = json.loads(sys.stdin.read() or "{}")
    url = str(request.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must be an absolute http(s) URL")
    max_scripts = int(request.get("max_scripts", 10))
    keywords = list(request.get("keywords") or ["약관", "판매중지", "판매중"])
    method = str(request.get("method") or "GET").upper()
    if method not in ("GET", "POST"):
        raise ValueError("method must be GET or POST")
    raw_limit = int(request.get("raw_limit", 0))
    raw_offset = int(request.get("raw_offset", 0))
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (SPS public disclosure probe)"
    if method == "POST":
        page = session.post(url, data=request.get("data") or {}, timeout=20)
    else:
        page = session.get(url, params=request.get("data") or None, timeout=20)
    html = page.text
    scripts = [urljoin(url, src) for src in _SCRIPT_SRC.findall(html)]
    # 사이트 자체 JS만 본다(공통 라이브러리 CDN 제외)
    own_scripts = [s for s in scripts if requests.utils.urlparse(s).netloc == requests.utils.urlparse(url).netloc]
    script_report = []
    for script_url in own_scripts[:max_scripts]:
        try:
            body = session.get(script_url, timeout=20).text
        except requests.RequestException as error:
            script_report.append({"url": script_url, "error": str(error)})
            continue
        script_report.append({
            "url": script_url,
            "endpoints": sorted(set(_ENDPOINT.findall(body)))[:40],
            "download_hints": [re.sub(r"\s+", " ", h) for h in _DOWNLOAD_HINT.findall(body)][:15],
        })
    print(json.dumps({
        "url": url,
        "status": page.status_code,
        "final_url": page.url,
        "length": len(html),
        "scripts": scripts,
        "page_endpoints": sorted(set(_ENDPOINT.findall(html)))[:60],
        "page_function_calls": sorted(set(_FUNC_CALL.findall(html)))[:40],
        "keyword_excerpts": _excerpts(html, keywords),
        "script_report": script_report,
        # 구조 확인용 원문 일부(raw_limit>0일 때만)
        "raw": html[raw_offset:raw_offset + raw_limit] if raw_limit > 0 else "",
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
