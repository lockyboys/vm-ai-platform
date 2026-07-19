from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path


PROJECT_ROOT = Path("/data/vm_project")
MAX_PATCH_BYTES = 1024 * 1024
MAX_PATCH_FILES = 50
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
FORBIDDEN_PATCH_MARKERS = (
    "GIT binary patch",
    "Binary files ",
    "deleted file mode ",
    "rename from ",
    "rename to ",
    "old mode ",
    "new mode ",
)


def _validate_relative_path(path: str) -> str:
    normalized_path = path.strip()
    relative_path = Path(normalized_path)
    if not normalized_path or relative_path.is_absolute():
        raise ValueError("Only non-empty project-relative paths are allowed.")
    if any(part in {"", ".", ".."} for part in relative_path.parts):
        raise ValueError("Dot segments are not allowed in patch paths.")
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_path.parts):
        raise ValueError("An excluded directory was requested.")
    if relative_path.name in DENIED_FILE_NAMES:
        raise ValueError("Environment files cannot be patched.")
    if relative_path.suffix.lower() in DENIED_SUFFIXES:
        raise ValueError("Secret-key files cannot be patched.")

    project_root = PROJECT_ROOT.resolve(strict=True)
    requested_path = (project_root / relative_path).resolve(strict=True)
    if project_root not in requested_path.parents:
        raise ValueError("The requested patch path is outside the project root.")
    if not requested_path.is_file():
        raise ValueError("Only existing regular files can be patched.")
    return str(requested_path.relative_to(project_root))


def _extract_patch_paths(patch_text: str) -> list[str]:
    old_paths = re.findall(r"^--- a/(.+)$", patch_text, flags=re.MULTILINE)
    new_paths = re.findall(r"^\+\+\+ b/(.+)$", patch_text, flags=re.MULTILINE)
    if not old_paths or len(old_paths) != len(new_paths):
        raise ValueError("Patch must contain matching --- a/ and +++ b/ paths.")
    if len(old_paths) > MAX_PATCH_FILES:
        raise ValueError(f"Patch exceeds the {MAX_PATCH_FILES}-file limit.")

    normalized_paths: list[str] = []
    for old_path, new_path in zip(old_paths, new_paths):
        if old_path != new_path:
            raise ValueError("File rename is not allowed by source_patch.")
        normalized_path = _validate_relative_path(old_path)
        if normalized_path not in normalized_paths:
            normalized_paths.append(normalized_path)
    return normalized_paths


def _file_sha256(path: str) -> str:
    content = (PROJECT_ROOT / path).read_bytes()
    return hashlib.sha256(content).hexdigest()


def _run_git_apply(patch_text: str, check_only: bool) -> subprocess.CompletedProcess[str]:
    arguments = ["git", "apply", "--whitespace=error-all"]
    if check_only:
        arguments.append("--check")
    arguments.append("-")
    return subprocess.run(
        arguments,
        cwd=PROJECT_ROOT,
        input=patch_text,
        capture_output=True,
        text=True,
        check=False,
    )


def source_patch(patch_text: str, dry_run: bool = True) -> dict:
    """Check or apply a text-only patch to existing project files."""
    if not patch_text.strip():
        raise ValueError("patch_text must not be empty.")
    patch_bytes = patch_text.encode("utf-8")
    if len(patch_bytes) > MAX_PATCH_BYTES:
        raise ValueError(f"Patch exceeds the {MAX_PATCH_BYTES}-byte limit.")
    for marker in FORBIDDEN_PATCH_MARKERS:
        if marker in patch_text:
            raise ValueError(f"Forbidden patch operation: {marker.strip()}")
    if "--- /dev/null" in patch_text or "+++ /dev/null" in patch_text:
        raise ValueError("File creation and deletion are not allowed by source_patch.")

    paths = _extract_patch_paths(patch_text)
    before_sha256 = {path: _file_sha256(path) for path in paths}

    check_result = _run_git_apply(patch_text, check_only=True)
    if check_result.returncode != 0:
        raise ValueError(check_result.stderr.strip() or "Patch check failed.")

    if dry_run:
        return {
            "dry_run": True,
            "applicable": True,
            "paths": paths,
            "patch_sha256": hashlib.sha256(patch_bytes).hexdigest(),
            "before_sha256": before_sha256,
        }

    apply_result = _run_git_apply(patch_text, check_only=False)
    if apply_result.returncode != 0:
        raise RuntimeError(apply_result.stderr.strip() or "Patch apply failed.")

    return {
        "dry_run": False,
        "applied": True,
        "paths": paths,
        "patch_sha256": hashlib.sha256(patch_bytes).hexdigest(),
        "before_sha256": before_sha256,
        "after_sha256": {path: _file_sha256(path) for path in paths},
    }
