"""Read-only inventory for every insurance PDF input; no file or database writes."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def main() -> int:
    """List every input PDF and report its content length without changing it."""
    project_root = Path(__file__).resolve().parents[2]
    pdf_root = Path(
        os.getenv(
            "AGENT_DOCUMENT_DIR",
            str(project_root / "FastAPI" / "LangGraph" / "insurance_docs"),
        )
    )
    pdf_files = sorted(path for path in pdf_root.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf")
    print(f"PDF_ROOT={pdf_root}")
    print(f"PDF_COUNT={len(pdf_files)}")
    if not pdf_files:
        return 2

    for pdf_path in pdf_files:
        raw = pdf_path.read_bytes()
        pages = "UNAVAILABLE"
        text_chars = "UNAVAILABLE"
        if PdfReader is not None:
            reader = PdfReader(str(pdf_path))
            pages = len(reader.pages)
            text_chars = sum(len(page.extract_text() or "") for page in reader.pages)
        print(
            f"FILE={pdf_path.name}\tBYTES={len(raw)}\tSHA256={hashlib.sha256(raw).hexdigest()}"
            f"\tPAGES={pages}\tTEXT_CHARS={text_chars}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
