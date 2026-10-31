"""삼성화재 보험상품공시실 약관 전용 다운로더.

공식 XML 카탈로그와 공식 JS의 검증된 규칙을 사용한다.
보험약관은 prdfilename1/file1.pdf이며, 기본은 dry-run이다.
MongoDB 적재는 하지 않으며, 다운로드 manifest를 다음 적재 단계의 입력으로 남긴다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

CATALOG_URL = "https://www.samsungfire.com/vh/page/VH.RPMY0133.do"
PDF_BASE_URL = "https://www.samsungfire.com"
SOURCE_PAGE = "https://www.samsungfire.com/vh/page/VH.REIF0012.do"
UA = "SPS-SamsungFire-Terms-Downloader/1.0"

def fetch(url: str, timeout: int = 60) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type", "")

def safe_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip()
    return value[:180] or "unnamed"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def catalog(include_stopped: bool) -> list[dict[str, str]]:
    raw, content_type = fetch(CATALOG_URL)
    if b"<terms" not in raw[:2000]:
        raise ValueError("삼성화재 XML 카탈로그가 아님")
    root = ET.fromstring(raw)
    rows = []
    for node in root.findall(".//product"):
        value = lambda tag: (node.findtext(tag) or "").strip()
        row = {
            "product_name": node.attrib.get("name", "").strip(),
            "product_gun": value("productgun"),
            "product_gubun": value("productgubun"),
            "channel": value("channel"),
            "product_code": value("productcode"),
            "gubun": value("gubun"),
            "sell_start": value("sellstart"),
            "sell_end": value("sellend"),
            "sell_end_status": value("sellendst"),
            "terms_file_yn": value("prdfilename1"),
            "catalog_content_type": content_type,
        }
        if not all(row[k] for k in ("product_name", "product_code", "gubun", "sell_start")):
            continue
        if row["terms_file_yn"] != "Y":
            continue
        if not include_stopped and row["sell_end_status"] != "N":
            continue
        row["url"] = f"{PDF_BASE_URL}/publication/pdf/{row['product_code']}_{row['gubun']}_{row['sell_start']}_file1.pdf"
        rows.append(row)
    return rows

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("/data/vm_project/outputs/insurance_docs/samsung_fire_terms"))
    parser.add_argument("--limit", type=int, default=0, help="0이면 전체")
    parser.add_argument("--offset", type=int, default=0, help="카탈로그 선택 시작 위치")
    parser.add_argument("--include-stopped", action="store_true")
    parser.add_argument("--apply", action="store_true", help="PDF 다운로드 실행")
    args = parser.parse_args()
    if args.limit < 0 or args.offset < 0:
        raise ValueError("--limit과 --offset은 0 이상이어야 함")
    rows = catalog(args.include_stopped)
    selected = rows[args.offset:args.offset + args.limit] if args.limit else rows[args.offset:]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_page": SOURCE_PAGE,
        "catalog_url": CATALOG_URL,
        "created_dt": datetime.now(timezone.utc).isoformat(),
        "dry_run": not args.apply,
        "include_stopped": args.include_stopped,
        "catalog_count": len(rows),
        "selected_count": len(selected),
        "documents": selected,
    }
    manifest_path = args.output_dir / "samsungfire_terms_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    downloaded = []
    if args.apply:
        for row in selected:
            data, content_type = fetch(row["url"])
            if not data.startswith(b"%PDF"):
                raise ValueError(f"PDF 검증 실패: {row['url']} ({content_type})")
            target = args.output_dir / safe_name(f"{row['product_name']}_{row['product_code']}_약관.pdf")
            target.write_bytes(data)
            downloaded.append({**row, "path": str(target), "bytes": len(data), "sha256": sha256(data)})
        (args.output_dir / "samsungfire_terms_downloaded.json").write_text(
            json.dumps(downloaded, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps({
        "dry_run": not args.apply,
        "catalog_count": len(rows),
        "selected_count": len(selected),
        "downloaded_count": len(downloaded),
        "manifest": str(manifest_path),
    }, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
