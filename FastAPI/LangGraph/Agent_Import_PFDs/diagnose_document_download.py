"""문서 다운로드 진단(읽기 전용, 파일 저장 없음).

입력(stdin JSON): {"profile_json": {...후보 프로파일...}, "file_name": "...", "variants": ["engine", "no_xrw", "browser_like"]}
각 방식으로 문서 요청을 한 번씩 보내고 상태코드·content-type·크기·앞/뒤 바이트만 보고한다.
목적: 브라우저에서는 PDF가 오는데 엔진 요청은 PDF가 아닐 때, 어떤 헤더 차이인지 프로그램이 스스로 판별하기 위함.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import urllib.request
from pathlib import Path

ENGINE = Path(__file__).resolve().with_name("public_document_catalog_collector.py")


def main() -> None:
    request = json.loads(sys.stdin.read() or "{}")
    spec = importlib.util.spec_from_file_location("engine_diag", ENGINE)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    profile = engine.validate_profile(request["profile_json"])
    document = profile["document"]
    url, form = engine.document_request(document, request["file_name"])
    if not url.startswith("http"):
        url = profile["base_url"] + url
    data = engine.encode_form(form, document.get("body_charset", "utf-8")) if form is not None else None
    base_headers = dict(profile["request"]["headers"])
    variants = {
        "engine": base_headers,
        "no_xrw": {k: v for k, v in base_headers.items() if k != "X-Requested-With"},
        "browser_like": {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                         "Referer": profile["base_url"] + "/", "Origin": profile["base_url"]},
    }
    report = []
    for name in request.get("variants") or list(variants):
        headers = dict(variants[name])
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=45) as resp:
                body = resp.read(30 * 1024 * 1024)
                report.append({"variant": name, "status": resp.status, "content_type": resp.headers.get("content-type"),
                               "disposition": resp.headers.get("content-disposition"), "bytes": len(body),
                               "head": body[:16].hex(), "tail": body[-32:].decode("latin-1", "replace"),
                               "text_preview": body[:300].decode("cp949", "replace") if not body.startswith(b"%PDF") else ""})
        except Exception as error:  # noqa: BLE001 - 진단 보고용
            report.append({"variant": name, "error": f"{type(error).__name__}: {str(error)[:200]}"})
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
