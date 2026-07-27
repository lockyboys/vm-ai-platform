from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path("/data/vm_project").resolve()
MAX_WRITE_BYTES = 2 * 1024 * 1024
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".home",
}
DENIED_FILE_NAMES = {".env", ".env.local", ".env.production"}
DENIED_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


def source_write(
    path: str,
    content: str,
    overwrite: bool = False,
    create_parent: bool = True,
) -> dict[str, Any]:
    """
    Atomically write one UTF-8 text file inside /data/vm_project.
    """

    normalized_path = path.strip()
    if not normalized_path:
        raise ValueError("path must not be empty.")

    relative_path = Path(normalized_path)

    if relative_path.is_absolute():
        raise ValueError(
            "path must be relative to the project root."
        )
    if any(part in {"", ".", ".."} for part in relative_path.parts):
        raise ValueError("Dot segments are not allowed in source paths.")
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_path.parts):
        raise ValueError("Writing to an excluded directory is not allowed.")
    if relative_path.name in DENIED_FILE_NAMES:
        raise ValueError("Writing environment files is not allowed.")
    if relative_path.suffix.lower() in DENIED_SUFFIXES:
        raise ValueError("Writing secret-key files is not allowed.")

    target_path = (
        PROJECT_ROOT / relative_path
    ).resolve()

    if (
        target_path != PROJECT_ROOT
        and PROJECT_ROOT not in target_path.parents
    ):
        raise ValueError(
            "The requested path is outside the project root."
        )

    existing_yn = target_path.exists()

    if existing_yn and not overwrite:
        raise FileExistsError(
            f"File already exists: {path}"
        )

    if create_parent:
        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
    elif not target_path.parent.exists():
        raise FileNotFoundError(
            f"Parent directory does not exist: "
            f"{target_path.parent}"
        )

    encoded_content = content.encode("utf-8")
    if len(encoded_content) > MAX_WRITE_BYTES:
        raise ValueError(
            f"content exceeds the {MAX_WRITE_BYTES}-byte write limit."
        )

    temporary_path = target_path.with_name(
        f".{target_path.name}.{uuid4().hex}.tmp"
    )

    try:
        with temporary_path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return {
        "path": str(
            target_path.relative_to(PROJECT_ROOT)
        ),
        "operation": (
            "UPDATED"
            if existing_yn
            else "CREATED"
        ),
        "bytes": len(encoded_content),
        "sha256": hashlib.sha256(
            encoded_content
        ).hexdigest(),
    }