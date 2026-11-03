"""소스 편집 보호 게이트.
부분 조회를 전체 소스로 오인하거나 검증 없이 재기동하는 것을 차단한다.
2026-10-31 보고서 6번째 대책 반영:
  - audit_backup(): 백업 + SHA256 증빙을 JSONL 로그에 기록
  - auto_backup_enabled(): 패치 도구에서 자동 백업 활성 여부 확인
"""
from __future__ import annotations
import ast, hashlib, json, shutil
from pathlib import Path
from datetime import datetime, timezone

# 감사 로그 경로 (monkeypatch 가능)
AUDIT_LOG_PATH = Path("/data/vm_project/harness/memory/source_edit_audit.jsonl")

class SourceEditGuardError(RuntimeError):
    pass

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def require_full_read(*, start_line: int, end_line: int, total_lines: int) -> None:
    if start_line != 1 or end_line != total_lines:
        raise SourceEditGuardError(
            f"full source required: start={start_line}, end={end_line}, total={total_lines}"
        )

def backup(path: Path) -> tuple[Path, str]:
    if not path.is_file():
        raise SourceEditGuardError(f"source not found: {path}")
    digest = sha256_text(path.read_text(encoding="utf-8"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    target = path.with_name(f"{path.name}.guard-{stamp}.bak")
    shutil.copy2(path, target)
    return target, digest

def validate_python(text: str, *, path: str = "<source>") -> None:
    try:
        ast.parse(text, filename=path)
    except SyntaxError as exc:
        raise SourceEditGuardError(f"python syntax invalid: {exc}") from exc

def require_entrypoint(text: str, *, markers: tuple[str, ...] = ("if __name__", "mcp.run", "uvicorn")) -> None:
    if not any(marker in text for marker in markers):
        raise SourceEditGuardError("required execution entrypoint is missing")

def verify_unchanged(path: Path, expected_sha256: str) -> None:
    actual = sha256_text(path.read_text(encoding="utf-8"))
    if actual != expected_sha256:
        raise SourceEditGuardError(f"source changed unexpectedly: {path}")

def audit_backup(path: Path) -> dict:
    """원본 백업 후 SHA256 증빙을 감사 로그(JSONL)에 기록한다.

    기록 항목:
      - timestamp: UTC ISO 형식
      - source_path: 원본 파일 경로
      - source_sha256: 원본 파일의 SHA256
      - backup_path: 백업 파일 경로
      - backup_sha256: 백업 파일의 SHA256 (원본과 동일해야 함)

    Returns:
        기록된 감사 레코드 (dict)
    """
    # 원본 백업 수행
    bak_path, source_digest = backup(path)
    backup_digest = sha256_text(bak_path.read_text(encoding="utf-8"))
    # 백업 무결성 검증: 원본과 백업의 해시가 일치해야 한다
    if source_digest != backup_digest:
        raise SourceEditGuardError(
            f"backup integrity failure: source={source_digest}, backup={backup_digest}"
        )
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_path": str(path),
        "source_sha256": source_digest,
        "backup_path": str(bak_path),
        "backup_sha256": backup_digest,
    }
    # 감사 로그에 추가 기록 (디렉터리 없으면 생성)
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record

def auto_backup_enabled() -> bool:
    """패치 도구에서 자동 백업이 활성화되어 있는지 반환한다."""
    return True

def status() -> dict:
    """소스 편집 보호 게이트의 공개 상태를 반환한다."""
    return {
        "guard": "source_edit_guard",
        "enabled": True,
        "requires_full_read_for_overwrite": True,
        "python_validation": True,
        "entrypoint_validation": True,
        "auto_backup": auto_backup_enabled(),
    }
