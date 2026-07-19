from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path("/data/vm_project")
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


def _resolve_project_write_path(path: str) -> tuple[Path, Path]:
    """Resolve a relative path and reject every project-root escape."""
    normalized_path = path.strip()
    if not normalized_path:
        raise ValueError("path must not be empty.")

    relative_path = Path(normalized_path)
    if relative_path.is_absolute():
        raise ValueError("Only project-relative paths are allowed.")
    if any(part in {"", ".", ".."} for part in relative_path.parts):
        raise ValueError("Dot segments are not allowed in source paths.")
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_path.parts):
        raise ValueError("Writing to an excluded directory is not allowed.")
    if relative_path.name in DENIED_FILE_NAMES:
        raise ValueError("Writing environment files is not allowed.")
    if relative_path.suffix.lower() in DENIED_SUFFIXES:
        raise ValueError("Writing secret-key files is not allowed.")

    project_root = PROJECT_ROOT.resolve(strict=True)
    requested_path = (project_root / relative_path).resolve(strict=False)
    if requested_path == project_root or project_root not in requested_path.parents:
        raise ValueError("The requested path is outside the project root.")
    return project_root, requested_path


def source_write(
    path: str,
    content: str,
    overwrite: bool = False,
    create_parent: bool = True,
) -> dict:
    """Atomically write one UTF-8 text file inside /data/vm_project."""
    project_root, requested_path = _resolve_project_write_path(path)
    encoded_content = content.encode("utf-8")
    if len(encoded_content) > MAX_WRITE_BYTES:
        raise ValueError(
            f"content exceeds the {MAX_WRITE_BYTES}-byte write limit."
        )

    existed_before = requested_path.exists()
    if existed_before and not requested_path.is_file():
        raise ValueError("The requested path exists and is not a file.")
    if existed_before and not overwrite:
        raise FileExistsError(
            "Source file already exists; set overwrite=true to replace it."
        )

    parent_path = requested_path.parent
    if not parent_path.exists():
        if not create_parent:
            raise FileNotFoundError("Parent directory does not exist.")
        parent_path.mkdir(parents=True, exist_ok=True)

    resolved_parent = parent_path.resolve(strict=True)
    if resolved_parent != project_root and project_root not in resolved_parent.parents:
        raise ValueError("The resolved parent directory is outside the project root.")

    temporary_path = parent_path / f".{requested_path.name}.{uuid4().hex}.tmp"
    try:
        with temporary_path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, requested_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return {
        "path": str(requested_path.relative_to(project_root)),
        "operation": "UPDATED" if existed_before else "CREATED",
        "bytes": len(encoded_content),
        "sha256": hashlib.sha256(encoded_content).hexdigest(),
    }
