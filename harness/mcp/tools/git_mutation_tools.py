# =============================================================================
# File Name   : harness/mcp/tools/git_mutation_tools.py
# Purpose     : 확인한 파일만 Git에 올리고 커밋하는 도구
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260902 | Codex | Harness 표준 파일 헤더와 커밋 대상 검증 역할을 보강했음
# =============================================================================
# 이 파일은 무엇을 하나요?
# - git_add와 git_stage_delete는 사용자가 고른 파일만 커밋 준비 상태로 만듭니다.
# - git_commit은 준비된 파일이 예상한 목록과 같을 때만 커밋합니다.
# 주의: 관련 없는 파일이 섞이면 커밋하지 않으며, 원격 저장소로 push하지 않습니다.
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path


PROJECT_ROOT = Path("/data/vm_project")
MAX_PATHS = 100
MAX_COMMIT_MESSAGE_LENGTH = 200
MAX_CACHED_PATCH_BYTES = 1024 * 1024
MAX_STAGED_DIFF_PREVIEW = 12000
FORBIDDEN_CACHED_PATCH_MARKERS = (
    "GIT " + "binary patch",
    "Binary " + "files ",
    "deleted " + "file mode ",
    "new " + "file mode ",
    "rename " + "from ",
    "rename " + "to ",
    "old " + "mode ",
    "new " + "mode ",
)
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".home",
}
DENIED_FILE_NAMES = {".env", ".env.local", ".env.production", "secrets.env"}
DENIED_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


def _run_git(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _validate_paths(paths: list[str], *, allow_deleted: bool = False) -> list[str]:
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
        if requested_path.exists():
            if not requested_path.is_file():
                raise ValueError("Only regular files can be staged.")
        elif allow_deleted:
            tracked_result = _run_git(
                ["ls-files", "--error-unmatch", "--", normalized_path]
            )
            if tracked_result.returncode != 0:
                raise ValueError("Only tracked deleted files can be staged.")
        else:
            raise ValueError("Only existing regular files can be staged.")

        canonical_path = str(requested_path.relative_to(project_root))
        if canonical_path not in normalized_paths:
            normalized_paths.append(canonical_path)

    return normalized_paths


def _staged_paths() -> list[str]:
    result = _run_git(["diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB"])
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


def _extract_cached_patch_paths(patch_text: str) -> list[str]:
    """Unified Diff 헤더에서 동일한 기존 파일 경로만 추출한다."""
    old_paths = re.findall(r"^--- a/(.+)$", patch_text, flags=re.MULTILINE)
    new_paths = re.findall(r"^\+\+\+ b/(.+)$", patch_text, flags=re.MULTILINE)
    if not old_paths or len(old_paths) != len(new_paths):
        raise ValueError("Patch must contain matching --- a/ and +++ b/ paths.")
    paths: list[str] = []
    for old_path, new_path in zip(old_paths, new_paths):
        if old_path != new_path:
            raise ValueError("Cached patch cannot create, delete, or rename files.")
        normalized = Path(old_path).as_posix()
        if normalized not in paths:
            paths.append(normalized)
    return paths


def _run_cached_patch(patch_text: str, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """작업 파일을 수정하지 않고 patch를 검사하거나 Git index에 적용한다."""
    return subprocess.run(
        ["git", "apply", "--unidiff-zero", "--whitespace=error-all", *arguments, "-"],
        cwd=PROJECT_ROOT,
        input=patch_text,
        capture_output=True,
        text=True,
        check=False,
    )


def git_apply_cached_patch(
    patch_text: str,
    expected_paths: list[str],
    dry_run: bool = True,
) -> dict:
    """검증된 Unified Diff의 선택 hunk만 Git index에 반영한다.

    작업 트리 파일은 절대 다시 쓰지 않는다. 먼저 patch가 현재 작업 트리에 실제로
    존재하는 변경인지 reverse-check하고, 현재 index에 적용 가능한지 cached-check한다.
    두 검사가 모두 통과한 경우에만 dry_run=False에서 index를 갱신한다.
    """
    if not isinstance(patch_text, str) or not patch_text.strip():
        raise ValueError("patch_text must be non-empty text.")
    patch_bytes = patch_text.encode("utf-8")
    if len(patch_bytes) > MAX_CACHED_PATCH_BYTES:
        raise ValueError(f"Patch exceeds the {MAX_CACHED_PATCH_BYTES}-byte limit.")
    for marker in FORBIDDEN_CACHED_PATCH_MARKERS:
        if marker in patch_text:
            raise ValueError(f"Forbidden cached patch operation: {marker.strip()}")
    if ("--- " + "/dev/null") in patch_text or ("+++ " + "/dev/null") in patch_text:
        raise ValueError("Cached patch cannot create or delete files.")

    patch_paths = _extract_cached_patch_paths(patch_text)
    requested_paths = [
        Path(path.strip().replace("\\", "/")).as_posix()
        for path in expected_paths
        if isinstance(path, str) and path.strip()
    ]
    if sorted(set(patch_paths)) != sorted(set(requested_paths)):
        raise ValueError(
            "Patch paths must exactly match expected_paths. "
            f"patch={sorted(set(patch_paths))}, expected={sorted(set(requested_paths))}")
    normalized_paths = _validate_paths(requested_paths)

    # reverse-check는 선택 patch의 변경 내용이 현재 worktree에 실제로 존재하는지
    # 확인하여 모델이 작업 파일에 없는 코드를 index에 꾸며 넣는 것을 차단한다.
    worktree_check = _run_cached_patch(patch_text, ["--reverse", "--check"])
    if worktree_check.returncode != 0:
        detail = worktree_check.stderr.strip()
        raise ValueError(
            "Patch does not describe changes present in the working tree"
            + (f": {detail}" if detail else "."))
    index_check = _run_cached_patch(patch_text, ["--cached", "--check"])
    if index_check.returncode != 0:
        raise ValueError(index_check.stderr.strip() or "Cached patch check failed.")

    patch_sha256 = hashlib.sha256(patch_bytes).hexdigest()
    if dry_run:
        return {
            "dry_run": True,
            "applicable": True,
            "paths": normalized_paths,
            "patch_sha256": patch_sha256,
            "staged_paths": _staged_paths(),
        }

    applied = _run_cached_patch(patch_text, ["--cached"])
    if applied.returncode != 0:
        raise RuntimeError(applied.stderr.strip() or "Cached patch apply failed.")
    staged = _run_git(["diff", "--cached", "--", *normalized_paths])
    if staged.returncode != 0:
        raise RuntimeError(staged.stderr.strip() or "Unable to verify staged patch.")
    if not staged.stdout.strip():
        raise RuntimeError("Cached patch applied but staged diff is empty.")
    return {
        "dry_run": False,
        "staged": True,
        "paths": normalized_paths,
        "patch_sha256": patch_sha256,
        "staged_paths": _staged_paths(),
        "staged_diff": staged.stdout[:MAX_STAGED_DIFF_PREVIEW],
        "staged_diff_truncated": len(staged.stdout) > MAX_STAGED_DIFF_PREVIEW,
        "staged_diff_sha256": hashlib.sha256(staged.stdout.encode("utf-8")).hexdigest(),
    }


def git_stage_delete(paths: list[str], dry_run: bool = True) -> dict:
    """Stage only explicit tracked files that have already been deleted."""
    normalized_paths = _validate_paths(paths, allow_deleted=True)
    for path in normalized_paths:
        if (PROJECT_ROOT / path).exists():
            raise ValueError("git_stage_delete accepts only already-deleted files.")

    arguments = ["add", "--update"]
    if dry_run:
        arguments.extend(["--dry-run", "--verbose"])
    arguments.extend(["--", *normalized_paths])

    result = _run_git(arguments)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git add --update failed.")

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

    normalized_expected_paths = sorted(_validate_paths(expected_paths, allow_deleted=True))
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
