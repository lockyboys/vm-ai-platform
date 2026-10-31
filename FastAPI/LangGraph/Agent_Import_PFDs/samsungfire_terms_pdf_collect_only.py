"""삼성화재 PDF 전용 병렬 수집 실행기.
MongoDB에는 연결하지 않고 공식 PDF와 manifest만 생성한다.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from samsungfire_terms_downloader import catalog, safe_name, fetch, sha256, SOURCE_PAGE, CATALOG_URL
from datetime import datetime, timezone

OUT = Path("/data/vm_project/outputs/insurance_docs/samsung_fire_terms")
WORKERS = 8

def download(row):
    data, content_type = fetch(row["url"], timeout=60)
    if not data.startswith(b"%PDF"):
        raise ValueError(f"PDF 검증 실패: {row['url']} ({content_type})")
    target = OUT / safe_name(f"{row['product_name']}_{row['product_code']}_약관.pdf")
    target.write_bytes(data)
    return {**row, "path": str(target), "bytes": len(data), "sha256": sha256(data)}

rows = catalog(False)
OUT.mkdir(parents=True, exist_ok=True)
downloaded = []
errors = []
with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    futures = {pool.submit(download, row): row for row in rows}
    for future in as_completed(futures):
        row = futures[future]
        try:
            downloaded.append(future.result())
        except Exception as exc:
            errors.append({"product_code": row.get("product_code"), "url": row.get("url"), "error": str(exc)})

downloaded.sort(key=lambda item: item["product_code"])
manifest = {
    "source_page": SOURCE_PAGE,
    "catalog_url": CATALOG_URL,
    "created_dt": datetime.now(timezone.utc).isoformat(),
    "mongo_ingest": False,
    "catalog_count": len(rows),
    "downloaded_count": len(downloaded),
    "error_count": len(errors),
    "documents": downloaded,
    "errors": errors,
}
manifest_path = OUT / "samsungfire_terms_downloaded_manifest.json"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"catalog_count": len(rows), "downloaded_count": len(downloaded), "error_count": len(errors), "manifest": str(manifest_path)}, ensure_ascii=False))
