"""삼성화재 약관 재수집기: 기존 유효 PDF는 보존하고 누락 항목만 공식 후보 URL로 재시도한다."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from datetime import datetime, timezone
from samsungfire_terms_downloader import catalog, safe_name, fetch, sha256, SOURCE_PAGE, CATALOG_URL

OUT = Path("/data/vm_project/outputs/insurance_docs/samsung_fire_terms")
WORKERS = 8

def download(row):
    target = OUT / safe_name(f"{row['product_name']}_{row['product_code']}_약관.pdf")
    if target.exists() and target.stat().st_size > 0:
        data = target.read_bytes()
        if data.startswith(b"%PDF"):
            return {**row, "path": str(target), "bytes": len(data), "sha256": sha256(data), "reused": True}
    urls = [row["url"]]
    prefix = row["url"].rsplit("_file", 1)[0]
    urls.extend(f"{prefix}_file{i}.pdf" for i in range(2, 6))
    errors = []
    for url in urls:
        try:
            data, content_type = fetch(url, timeout=60)
            if data.startswith(b"%PDF"):
                target.write_bytes(data)
                return {**row, "url": url, "path": str(target), "bytes": len(data), "sha256": sha256(data), "reused": False}
            errors.append(f"{url}: not PDF ({content_type})")
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("; ".join(errors))

rows = catalog(False)
OUT.mkdir(parents=True, exist_ok=True)
downloaded, errors = [], []
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
