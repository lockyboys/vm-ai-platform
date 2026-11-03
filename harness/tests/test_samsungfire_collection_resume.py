"""회귀 테스트: 삼성화재 전체 버전 수집기의 재개·검증 상태 보존 기능을 확인한다."""

import ast
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "FastAPI/LangGraph/Agent_Import_PFDs/samsungfire_terms_pdf_collect_all_versions.py"
FUNCTIONS = {
    "row_key",
    "pdf_path",
    "is_valid_pdf",
    "verify_rows",
    "seed_existing_documents",
    "atomic_write_json",
    "merge_result",
    "load_checkpoint",
}


def load_pure_helpers():
    """수집기 최상위 코드를 실행하지 않고 순수 헬퍼 함수만 테스트용으로 불러온다."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    nodes = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in FUNCTIONS
    ]
    namespace = {
        "Path": Path,
        "json": json,
        "OUT": Path("/tmp/sps-unused-samsungfire-test"),
        "safe_name": lambda value: value.replace("/", "_"),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SCRIPT), "exec"), namespace)
    return namespace


def test_verify_rows_counts_missing_and_invalid_pdfs(tmp_path):
    """실패 검증: 누락 파일과 PDF 헤더가 잘못된 파일은 완료 수에 포함하지 않는다."""
    helpers = load_pure_helpers()
    valid = {"product_code": "A1", "sell_start": "20260101", "product_name": "valid"}
    missing = {"product_code": "A2", "sell_start": "20260101", "product_name": "missing"}
    invalid = {"product_code": "A3", "sell_start": "20260101", "product_name": "invalid"}
    helpers["pdf_path"](valid, tmp_path).write_bytes(b"%PDF-1.7\nbody\n%%EOF")
    helpers["pdf_path"](invalid, tmp_path).write_bytes(b"not a pdf")

    result = helpers["verify_rows"]([valid, missing, invalid], tmp_path)

    assert result["catalog_count"] == 3
    assert result["downloaded_count"] == 1
    assert result["missing_count"] == 2


def test_verified_existing_files_seed_resume_state():
    """기존에 검증된 PDF는 재개 manifest에서 이미 완료된 약관으로 취급한다."""
    helpers = load_pure_helpers()
    row = {"product_code": "A1", "sell_start": "20260101", "product_name": "valid"}
    path = "/tmp/valid_A1_20260101.pdf"
    present = [{"key": helpers["row_key"](row), "path": path, "bytes": 128}]

    documents = helpers["seed_existing_documents"]([row], present)

    assert documents[helpers["row_key"](row)]["path"] == path
    assert documents[helpers["row_key"](row)]["reused"] is True


def test_atomic_write_json_replaces_checkpoint_without_temp_residue(tmp_path):
    """진행 manifest를 원자적으로 기록하고 임시 파일을 남기지 않는다."""
    helpers = load_pure_helpers()
    target = tmp_path / "progress.json"
    payload = {"downloaded_count": 2, "complete": False}

    helpers["atomic_write_json"](target, payload)

    assert json.loads(target.read_text(encoding="utf-8")) == payload
    assert not target.with_suffix(".json.tmp").exists()


def test_merge_result_clears_prior_error_after_success():
    """재시도 성공 시 같은 약관의 이전 실패 상태를 제거한다."""
    helpers = load_pure_helpers()
    row = {"product_code": "A1", "sell_start": "20260101"}
    documents = {}
    errors = {}

    helpers["merge_result"](documents, errors, row, error="temporary failure")
    helpers["merge_result"](documents, errors, row, result={"path": "A1.pdf", "sha256": "abc"})

    assert helpers["row_key"](row) in documents
    assert helpers["row_key"](row) not in errors


def test_main_guard_prevents_downloads_when_imported():
    """수집기 import만으로 네트워크 다운로드가 시작되지 않도록 main guard를 요구한다."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    guarded = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        for node in tree.body
    )

    assert guarded


def test_load_checkpoint_rejects_corrupt_and_stale_documents(tmp_path):
    """손상 PDF와 현재 카탈로그 밖 문서는 복원하지 않고 현재 오류만 유지한다."""
    helpers = load_pure_helpers()
    current = {"product_code": "A1", "sell_start": "20260101"}
    stale = {"product_code": "A2", "sell_start": "20250101"}
    corrupt_path = tmp_path / "corrupt.pdf"
    stale_path = tmp_path / "stale.pdf"
    corrupt_path.write_bytes(b"not a valid pdf")
    stale_path.write_bytes(b"%PDF-1.7\nbody\n%%EOF")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "documents": [
            {**current, "path": str(corrupt_path)},
            {**stale, "path": str(stale_path)},
        ],
        "errors": [
            {**current, "error": "retryable"},
            {**stale, "error": "stale"},
        ],
    }), encoding="utf-8")

    documents, errors = helpers["load_checkpoint"](manifest, {helpers["row_key"](current)})

    assert documents == {}
    assert list(errors) == [helpers["row_key"](current)]


def test_merge_result_failure_removes_stale_success_document():
    """재시도 실패 시 과거 성공 문서를 제거해 manifest가 모순되지 않게 한다."""
    helpers = load_pure_helpers()
    row = {"product_code": "A1", "sell_start": "20260101", "url": "https://example.invalid/a1.pdf"}
    key = helpers["row_key"](row)
    documents = {key: {"path": "old.pdf", "sha256": "old"}}
    errors = {}

    helpers["merge_result"](documents, errors, row, error="download failed")

    assert key not in documents
    assert errors[key]["error"] == "download failed"
