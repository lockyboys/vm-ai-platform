"""삼성화재 판매중·판매종료 전체 약관을 재개 가능한 배치로 수집한다."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.error import HTTPError

from samsungfire_terms_downloader import (
    catalog,
    safe_name,
    fetch,
    sha256,
    SOURCE_PAGE,
    CATALOG_URL,
)

OUT = Path("/data/vm_project/outputs/insurance_docs/samsung_fire_terms_all_versions")
DEFAULT_LIMIT = 20
DEFAULT_WORKERS = 4
DEFAULT_TIMEOUT = 12
MANIFEST_NAME = "samsungfire_terms_all_versions_manifest.json"


def row_key(row: dict) -> str:
    """보험 상품 코드와 판매 시작일로 한 약관 버전을 식별한다."""
    return f"{row.get('product_code', '')}:{row.get('sell_start', '')}"


def pdf_path(row: dict, output_dir: Path = OUT) -> Path:
    """기존 파일명 규칙을 유지해 이 버전의 저장 경로를 만든다."""
    filename = f"{row['product_name']}_{row['product_code']}_{row['sell_start']}_약관.pdf"
    return Path(output_dir) / safe_name(filename)


def is_valid_pdf(path: Path) -> bool:
    """잘린 다운로드를 재사용하지 않도록 PDF 헤더와 끝 표식을 검사한다."""
    try:
        size = path.stat().st_size
        if size < 16:
            return False
        with path.open("rb") as stream:
            header = stream.read(8)
            stream.seek(max(0, size - 4096))
            trailer = stream.read()
        return header.startswith(b"%PDF-") and b"%%EOF" in trailer
    except OSError:
        return False


def verify_rows(rows: list[dict], output_dir: Path = OUT) -> dict:
    """카탈로그 각 버전에 대해 현재 유효 PDF와 누락 항목을 센다."""
    present = []
    missing = []
    for row in rows:
        target = pdf_path(row, output_dir)
        if is_valid_pdf(target):
            present.append({
                "key": row_key(row),
                "product_code": row.get("product_code"),
                "sell_start": row.get("sell_start"),
                "product_name": row.get("product_name"),
                "path": str(target),
                "bytes": target.stat().st_size,
            })
        else:
            missing.append({
                "key": row_key(row),
                "product_code": row.get("product_code"),
                "sell_start": row.get("sell_start"),
                "product_name": row.get("product_name"),
                "expected_path": str(target),
            })
    return {
        "catalog_count": len(rows),
        "downloaded_count": len(present),
        "missing_count": len(missing),
        "present": present,
        "missing": missing,
    }


def seed_existing_documents(rows: list[dict], present: list[dict]) -> dict:
    """검증된 기존 PDF를 manifest 진행 상태에 반영해 다시 받지 않도록 한다."""
    row_by_key = {row_key(row): row for row in rows}
    documents = {}
    for item in present:
        key = item["key"]
        row = row_by_key.get(key)
        if row is not None:
            documents[key] = {
                **row,
                "path": item["path"],
                "bytes": item["bytes"],
                "reused": True,
            }
    return documents


def atomic_write_json(path: Path, payload: dict) -> None:
    """중간 종료에도 manifest가 반쯤 쓰이지 않도록 임시 파일을 교체한다."""
    path = Path(path)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def merge_result(documents: dict, errors: dict, row: dict, result: dict | None = None, error: str | None = None) -> None:
    """같은 버전의 재시도 결과를 합치고 성공하면 과거 실패를 지운다."""
    key = row_key(row)
    if result is not None:
        documents[key] = result
        errors.pop(key, None)
    elif error is not None:
        documents.pop(key, None)
        errors[key] = {
            "product_code": row.get("product_code"),
            "sell_start": row.get("sell_start"),
            "url": row.get("url"),
            "error": error,
        }


def load_checkpoint(manifest_path: Path, valid_keys: set[str]) -> tuple[dict, dict]:
    """기존 진행 기록에서 현재 카탈로그에 속한 유효 파일과 오류만 복구한다."""
    if not manifest_path.exists():
        return {}, {}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents = {}
    errors = {}
    for item in payload.get("documents", []):
        key = row_key(item)
        if key in valid_keys and is_valid_pdf(Path(item.get("path", ""))):
            documents[key] = item
    for item in payload.get("errors", []):
        key = row_key(item)
        if key in valid_keys and key not in documents:
            errors[key] = item
    return documents, errors


def make_manifest(rows: list[dict], documents: dict, errors: dict, batch: dict) -> dict:
    """모든 배치에서 누적 성공·실패·대기 수를 같은 manifest에 기록한다."""
    valid_keys = {row_key(row) for row in rows}
    docs = [documents[key] for key in sorted(documents) if key in valid_keys]
    failed = [errors[key] for key in sorted(errors) if key in valid_keys and key not in documents]
    processed = {row_key(item) for item in docs} | {row_key(item) for item in failed}
    pending_count = len(valid_keys - processed)
    return {
        "source_page": SOURCE_PAGE,
        "catalog_url": CATALOG_URL,
        "updated_dt": datetime.now(timezone.utc).isoformat(),
        "mongo_ingest": False,
        "include_stopped": True,
        "catalog_count": len(valid_keys),
        "downloaded_count": len(docs),
        "error_count": len(failed),
        "pending_count": pending_count,
        "complete": pending_count == 0 and len(failed) == 0,
        "documents": docs,
        "errors": failed,
        "last_batch": batch,
    }


def download(row: dict, output_dir: Path = OUT, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """유효 PDF는 재사용하고, 누락 파일은 공식 후보 URL에서 내려받아 원자 교체한다."""
    target = pdf_path(row, output_dir)
    if is_valid_pdf(target):
        data = target.read_bytes()
        return {**row, "path": str(target), "bytes": len(data), "sha256": sha256(data), "reused": True}

    # 공식 카탈로그의 기본 PDF와 file2~file5 대체 문서 링크를 순서대로 확인한다.
    urls = [row["url"]]
    prefix = row["url"].rsplit("_file", 1)[0]
    urls.extend(f"{prefix}_file{i}.pdf" for i in range(2, 6))
    errors = []
    target.parent.mkdir(parents=True, exist_ok=True)
    for url in urls:
        try:
            data, content_type = fetch(url, timeout=timeout)
            if not data.startswith(b"%PDF"):
                errors.append(f"{url}: not PDF ({content_type})")
                continue
            # .part 파일이 완전히 검증된 뒤에만 최종 PDF 경로로 바꾼다.
            temp_path = target.with_name(target.name + ".part")
            temp_path.write_bytes(data)
            if not is_valid_pdf(temp_path):
                temp_path.unlink(missing_ok=True)
                errors.append(f"{url}: PDF header/trailer validation failed")
                continue
            temp_path.replace(target)
            return {**row, "url": url, "path": str(target), "bytes": len(data), "sha256": sha256(data), "reused": False}
        except HTTPError as exc:
            errors.append(f"{url}: HTTP {exc.code}: {exc.reason}")
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("; ".join(errors))


def main(argv: list[str] | None = None) -> int:
    """한 번에 제한된 수만 처리하고, 다음 실행은 manifest의 다음 누락부터 재개한다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="카탈로그와 로컬 PDF만 확인하고 다운로드하지 않는다.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="이번 실행에서 처리할 최대 버전 수(0이면 남은 전체).")
    parser.add_argument("--offset", type=int, default=None, help="명시한 카탈로그 위치부터 처리한다. 생략하면 진행 manifest 기준으로 재개한다.")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="동시 다운로드 수(1~8).")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="후보 URL 하나의 HTTP 제한 시간(초).")
    parser.add_argument("--retry-errors", action="store_true", help="대기 항목보다 기존 실패 항목을 먼저 재시도한다.")
    args = parser.parse_args(argv)
    if args.limit < 0 or args.offset is not None and args.offset < 0:
        parser.error("--limit과 --offset은 0 이상이어야 합니다.")
    if not 1 <= args.workers <= 8 or not 1 <= args.timeout <= 60:
        parser.error("--workers는 1~8, --timeout은 1~60이어야 합니다.")

    # 판매중과 판매종료를 모두 포함한 공식 카탈로그를 매 실행마다 새로 확인한다.
    rows = catalog(True)
    audit = verify_rows(rows, OUT)
    if args.verify_only:
        print(json.dumps(audit, ensure_ascii=False))
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / MANIFEST_NAME
    valid_keys = {row_key(row) for row in rows}
    documents, errors = load_checkpoint(manifest_path, valid_keys)
    # 이전 실행에서 manifest 전에 받은 PDF도 검증 결과를 바탕으로 성공으로 편입한다.
    for key, item in seed_existing_documents(rows, audit["present"]).items():
        documents.setdefault(key, item)
        errors.pop(key, None)

    if args.offset is not None:
        end = None if args.limit == 0 else args.offset + args.limit
        selected = rows[args.offset:end]
    else:
        # 성공·실패 기록이 없는 항목부터 처리해 재호출마다 자동으로 다음 배치로 이동한다.
        unattempted = [row for row in rows if row_key(row) not in documents and row_key(row) not in errors]
        failed = [row for row in rows if row_key(row) in errors]
        candidates = failed + unattempted if args.retry_errors else unattempted
        selected = candidates if args.limit == 0 else candidates[:args.limit]

    batch = {"offset": args.offset, "limit": args.limit, "selected_count": len(selected), "retry_errors": args.retry_errors, "filesystem_before": {"downloaded_count": audit["downloaded_count"], "missing_count": audit["missing_count"]}}
    atomic_write_json(manifest_path, make_manifest(rows, documents, errors, batch))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(download, row, OUT, args.timeout): row for row in selected}
        for future in as_completed(futures):
            row = futures[future]
            try:
                merge_result(documents, errors, row, result=future.result())
            except Exception as exc:
                merge_result(documents, errors, row, error=str(exc))
            # 각 항목이 끝날 때마다 원자적으로 저장해 MCP 중단 후 이어받는다.
            atomic_write_json(manifest_path, make_manifest(rows, documents, errors, batch))

    result = make_manifest(rows, documents, errors, batch)
    print(json.dumps({
        "catalog_count": result["catalog_count"],
        "downloaded_count": result["downloaded_count"],
        "error_count": result["error_count"],
        "pending_count": result["pending_count"],
        "complete": result["complete"],
        "manifest": str(manifest_path),
        "last_batch": batch,
        "filesystem_before": batch["filesystem_before"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
