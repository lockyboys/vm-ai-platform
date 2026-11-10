"""검증된 소스 수정안을 "백업 → 적용 → 검증 → 실패 시 되돌림"으로 처리하는 재사용 모듈 (2026-11-10).

처음에는 review_python_source(multi_persona_tools.py) 안에만 있던 자동 수정 로직을
다른 MCP 도구에서도 쓸 수 있도록 분리했다(LuckyBoys 요청).

사용법
    from harness.mcp.tools.auto_apply import validate_test_paths, apply_with_rollback
    tests = validate_test_paths(["tests/test_x.py"], project_root)       # 제출 단계에서 입력 검사
    state = apply_with_rollback(source, proposed, job_dir, expected_sha256,
                                tests, budget_seconds, project_root)     # 워커 단계에서 적용

동작 순서 (apply_with_rollback)
    1) 남은 시간(budget)이 30초 미만이면 적용하지 않는다.
    2) 원본 해시가 제출 당시(expected_sha256)와 다르면 덮어쓰지 않는다(다른 작업 보호).
    3) 원본을 backup_dir/original.py로 백업한다(일반 지침 7: 원본 보존).
    4) 제안 소스로 교체 → 문법 컴파일 → test_paths가 있으면 pytest 실행.
    5) 컴파일 오류·테스트 실패·시간 초과 중 하나라도 나면 백업으로 자동 복원한다.
    6) Git 커밋은 하지 않는다(사람이 확인 후 지시).

⚠ 주의: test_paths 없이 호출하면 문법만 맞아도 원본이 바뀐다(동작이 달라져도 되돌리지 않음).
  중요한 파일은 반드시 test_paths=["tests/...", "harness/tests/..."]를 함께 넘길 것.
  허용 폴더와 pytest 시간 상한은 루트 config.py에서 읽는다(일반 지침 4, 하드코딩 금지):
    - MULTI_PERSONA_AUTO_APPLY_TEST_ROOTS
    - MULTI_PERSONA_AUTO_APPLY_TEST_TIMEOUT_SECONDS
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import config as project_config
from harness.mcp.tools.execution_tools import _mask_secrets


def validate_test_paths(values, project_root: Path) -> list[str]:
    """자동 적용 후 돌릴 테스트 경로를 설정된 테스트 폴더 안으로만 제한한다.

    잘못된 입력(목록이 아님, 문자열이 아닌 값, 빈 문자열, 경로 탈출, 테스트 폴더 밖, 없는 파일)은
    작업을 시작하기 전에 거부해 워커가 임의 코드를 '테스트'로 실행하지 못하게 한다.
    반환값은 project_root 기준 상대 경로 목록이다.
    """
    if values is None:
        return []
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError("test_paths must be a list of text paths")
    root = Path(project_root).resolve()
    allowed = [(root / name).resolve() for name in project_config.MULTI_PERSONA_AUTO_APPLY_TEST_ROOTS]
    checked = []
    for value in values:
        if not value.strip():
            raise ValueError("test_paths must not contain empty paths")
        path = (root / Path(value).expanduser()).resolve()  # 심볼릭 링크까지 풀어서 실제 위치 확인
        if root not in path.parents:
            raise ValueError("test_paths must stay inside the project")
        if not any(path == folder or folder in path.parents for folder in allowed):
            raise ValueError("test_paths must stay inside the configured test folders")
        if not path.exists():
            raise FileNotFoundError(f"Test path not found: {value}")
        checked.append(str(path.relative_to(root)))
    return checked


def apply_with_rollback(source: Path, proposed: Path, backup_dir: Path, expected_sha256: str,
                        test_paths: list[str], budget: float, project_root: Path) -> dict:
    """검증된 제안을 원본에 적용하고, 검증에 실패하면 원본으로 되돌린다.

    반환 dict(그대로 결과 파일에 남기는 것을 전제로 한다):
      applied, rolled_back, reason, backup_path, test_returncode, test_output_tail
    """
    root = Path(project_root)
    state = {"auto_apply": True, "applied": False, "rolled_back": False, "reason": None,
             "backup_path": None, "test_returncode": None}
    if budget < 30:
        state["reason"] = "not enough time left after review"
        return state
    # 작업 도중 사람이나 다른 작업이 원본을 바꿨다면 덮어쓰지 않는다.
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected_sha256:
        state["reason"] = "source changed during review"
        return state
    backup = backup_dir / "original.py"
    shutil.copy2(source, backup)
    backup.chmod(0o600)  # 원본 사본은 소유자만 읽도록 제한
    original_bytes = backup.read_bytes()
    state["backup_path"] = str(backup.relative_to(root))
    try:
        source.write_bytes(proposed.read_bytes())
        # 파일(.pyc)을 만들지 않고 문법만 확인한다.
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
        # ⚠ test_paths가 비어 있으면 여기서 끝난다 = 문법만 맞으면 제안이 원본에 남는다.
        if test_paths:
            run = subprocess.run(
                [str(root / "venv/bin/python"), "-m", "pytest", "-q", *test_paths],
                cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                # 설정 상한과 남은 시간 중 작은 값(결과 저장 여유 10초 확보)
                timeout=max(1, min(int(project_config.MULTI_PERSONA_AUTO_APPLY_TEST_TIMEOUT_SECONDS),
                                   int(budget) - 10)),
                check=False)
            state["test_returncode"] = run.returncode
            state["test_output_tail"] = _mask_secrets(run.stdout.decode("utf-8", errors="replace"))[-2000:]
            if run.returncode != 0:
                raise RuntimeError("tests failed after applying the proposal")
        state["applied"] = True
    except Exception as error:  # 컴파일 오류·테스트 실패·시간 초과 모두 되돌린다
        source.write_bytes(original_bytes)
        state.update(rolled_back=True, reason=f"{type(error).__name__}: {error}"[:500])
    return state
