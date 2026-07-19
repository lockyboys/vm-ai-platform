from __future__ import annotations

import subprocess
from pathlib import Path


PROJECT_ROOT = Path("/data/vm_project")
MAX_PATHS = 100
MAX_COMMIT_MESSAGE_LENGTH = 200
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


def _run_git(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _validate_paths(paths: list[str]) -> list[str]:
    if not paths:
        raise ValueError("At least one explicit path is required.")
    if len(paths) > MAX_PATHS:
        raise ValueError(f"No more than {MAX_PATHS} paths are allowed.")

    project_root = PROJECT_ROOT.resolve(strict=True)
    normalized_paths: list[str] = []

    for path in paths:
        normalized_path = path.strip()
        if not normalized_path:
            raise ValueError("Git paths must not be empty.")

        relative_path = Path(normalized_path)
        if relative_path.is_absolute():
            raise ValueError("Only project-relative Git paths are allowed.")
        if any(part in {"", ".", ".."} for part in relative_path.parts):
            raise ValueError("Dot segments are not allowed in Git paths.")
        if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_path.parts):
            raise ValueError("An excluded directory was requested.")
        if relative_path.name in DENIED_FILE_NAMES:
            raise ValueError("Environment files cannot be staged.")
        if relative_path.suffix.lower() in DENIED_SUFFIXES:
            raise ValueError("Secret-key files cannot be staged.")

        requested_path = (project_root / relative_path).resolve(strict=False)
        if requested_path == project_root or project_root not in requested_path.parents:
            raise ValueError("The requested Git path is outside the project root.")
        if not requested_path.exists() or not requested_path.is_file():
            raise ValueError("Only existing regular files can be staged.")

        canonical_path = str(requested_path.relative_to(project_root))
        if canonical_path not in normalized_paths:
            normalized_paths.append(canonical_path)

    return normalized_paths


def _staged_paths() -> list[str]:
    result = _run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to read staged files.")
    return sorted(line for line in result.stdout.splitlines() if line)


def git_add(paths: list[str], dry_run: bool = True) -> dict:
    """Stage explicit existing files; deletions and broad pathspecs are rejected."""
    normalized_paths = _validate_paths(paths)
    arguments = ["add"]
    if dry_run:
        arguments.extend(["--dry-run", "--verbose"])
    arguments.extend(["--", *normalized_paths])

    result = _run_git(arguments)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git add failed.")

    return {
        "dry_run": dry_run,
        "requested_paths": normalized_paths,
        "staged_paths": _staged_paths(),
        "git_output": result.stdout.splitlines(),
    }


def git_commit(
    message: str,
    expected_paths: list[str],
    dry_run: bool = True,
) -> dict:
    """Commit only when the exact expected set is staged. Never push."""
    normalized_message = message.strip()
    if not normalized_message:
        raise ValueError("Commit message must not be empty.")
    if "\n" in normalized_message or "\r" in normalized_message:
        raise ValueError("Commit message must be a single line.")
    if len(normalized_message) > MAX_COMMIT_MESSAGE_LENGTH:
        raise ValueError(
            f"Commit message exceeds {MAX_COMMIT_MESSAGE_LENGTH} characters."
        )

    normalized_expected_paths = sorted(_validate_paths(expected_paths))
    actual_staged_paths = _staged_paths()
    if not actual_staged_paths:
        raise ValueError("There are no staged files to commit.")
    if actual_staged_paths != normalized_expected_paths:
        raise ValueError(
            "Staged files do not exactly match expected_paths. "
            f"expected={normalized_expected_paths}, actual={actual_staged_paths}"
        )

    if dry_run:
        return {
            "dry_run": True,
            "would_commit": True,
            "message": normalized_message,
            "staged_paths": actual_staged_paths,
        }

    result = _run_git(
        [
            "commit",
            "-m",
            normalized_message,
        ]
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "git commit failed."
        )

    return {
        "dry_run": False,
        "committed": True,
        "message": normalized_message,
        "committed_paths": actual_staged_paths,
        "git_output": result.stdout.splitlines(),
        "remaining_staged_paths": _staged_paths(),
    }
