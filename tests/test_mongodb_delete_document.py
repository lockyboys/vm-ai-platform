from pathlib import Path
import runpy

_suite = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "harness/tests/test_mongodb_delete_document.py")
)

test_mongodb_delete_document_dry_run_does_not_delete = _suite[
    "test_mongodb_delete_document_dry_run_does_not_delete"
]
test_mongodb_delete_document_apply_deletes_exact_document = _suite[
    "test_mongodb_delete_document_apply_deletes_exact_document"
]
test_mongodb_delete_document_requires_valid_object_id = _suite[
    "test_mongodb_delete_document_requires_valid_object_id"
]
