"""스스로 고치는 앱의 '적용·검증·되돌림' 모듈 — 검증된 소스 수정안을
"백업 → 적용 → 검증 → 실패 시 되돌림"으로 처리하는 재사용 모듈 (2026-11-10, 2026-11-11 명시).

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

적용 규칙(policy, 2026-11-11 추가 — LuckyBoys 요청: "일부라도 반영되게")
    - "all_pass": 테스트가 전부 통과해야만 적용한다(이전 동작).
    - "improve" : 적용 전에 원본으로 같은 테스트를 먼저 돌려 통과한 테스트 목록을 기록한다(기준선).
                  제안 적용 후 (a) 기준선에서 통과하던 테스트가 하나도 새로 실패하지 않고
                  (b) 통과한 테스트 수가 늘었으면 일부 개선으로 보고 적용한다(partial=True).
                  둘 중 하나라도 아니면 되돌린다. 테스트별 결과는 pytest --junitxml로 읽는다
                  (결과 파일을 못 읽으면 판단 근거가 없으므로 되돌린다).
    - 기본값은 루트 config.py의 MULTI_PERSONA_AUTO_APPLY_POLICY에서 읽는다.
    - 컴파일 오류는 규칙과 관계없이 항상 되돌린다.

⚠ 주의: test_paths 없이 호출하면 문법만 맞아도 원본이 바뀐다(동작이 달라져도 되돌리지 않음).
  중요한 파일은 반드시 test_paths=["tests/...", "harness/tests/..."]를 함께 넘길 것.
  허용 폴더와 pytest 시간 상한은 루트 config.py에서 읽는다(일반 지침 4, 하드코딩 금지):
    - MULTI_PERSONA_AUTO_APPLY_TEST_ROOTS
    - MULTI_PERSONA_AUTO_APPLY_TEST_TIMEOUT_SECONDS
    - MULTI_PERSONA_AUTO_APPLY_POLICY
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import config as project_config
from harness.mcp.tools.execution_tools import _mask_secrets

# 허용하는 적용 규칙 이름(잘못된 값은 ValueError로 거부한다).
APPLY_POLICIES = ("all_pass", "improve")


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


def resolve_policy(policy=None) -> str:
    """적용 규칙 이름을 확정한다. None이면 config 기본값, 허용 목록 밖이면 ValueError."""
    value = policy if policy is not None else getattr(project_config, "MULTI_PERSONA_AUTO_APPLY_POLICY", "all_pass")
    if value not in APPLY_POLICIES:
        raise ValueError(f"apply policy must be one of {APPLY_POLICIES}: {value!r}")
    return value


def _passed_tests(xml_path: Path):
    """pytest --junitxml 결과에서 (통과한 테스트 id 집합, 전체 수)를 읽는다. 파일이 없거나 깨지면 None."""
    try:
        root = ET.parse(xml_path).getroot()
    except (OSError, ET.ParseError):
        return None
    passed, total = set(), 0
    for case in root.iter("testcase"):
        total += 1
        # failure·error·skipped 하위 요소가 없으면 통과로 본다.
        if not any(case.find(tag) is not None for tag in ("failure", "error", "skipped")):
            passed.add(f"{case.get('classname')}::{case.get('name')}")
    return passed, total


def _run_tests(root: Path, test_paths: list[str], deadline: float, xml_path: Path):
    """pytest를 한 번 실행한다. 반환: (returncode, 출력 끝부분, 통과 결과 또는 None).

    시간 상한 = config 상한과 남은 시간(결과 저장 여유 10초 확보) 중 작은 값.
    """
    timeout = max(1, min(int(project_config.MULTI_PERSONA_AUTO_APPLY_TEST_TIMEOUT_SECONDS),
                         int(deadline - time.monotonic()) - 10))
    xml_path.unlink(missing_ok=True)  # 이전 결과가 남아 잘못 읽히지 않도록 지운다
    run = subprocess.run(
        [str(root / "venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
         f"--junitxml={xml_path}", *test_paths],
        cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=timeout, check=False)
    tail = _mask_secrets(run.stdout.decode("utf-8", errors="replace"))[-2000:]
    return run.returncode, tail, _passed_tests(xml_path)


def apply_with_rollback(source: Path, proposed: Path, backup_dir: Path, expected_sha256: str,
                        test_paths: list[str], budget: float, project_root: Path, policy=None) -> dict:
    """검증된 제안을 원본에 적용하고, 검증에 실패하면 원본으로 되돌린다.

    policy: "all_pass" | "improve" | None(config 기본값). 자세한 규칙은 모듈 설명 참고.
    반환 dict(그대로 결과 파일에 남기는 것을 전제로 한다):
      applied, rolled_back, reason, backup_path, test_returncode, test_output_tail,
      policy, partial, tests_total, tests_passed_before, tests_passed_after, newly_failed
    """
    root = Path(project_root)
    policy = resolve_policy(policy)
    deadline = time.monotonic() + budget
    state = {"auto_apply": True, "applied": False, "rolled_back": False, "reason": None,
             "backup_path": None, "test_returncode": None, "policy": policy, "partial": False}
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
    baseline = None
    if policy == "improve" and test_paths:
        # 기준선: 원본 그대로 같은 테스트를 돌려 통과 목록을 기록한다(원본은 아직 바꾸지 않음).
        _code, _tail, baseline = _run_tests(root, test_paths, deadline, backup_dir / "junit_before.xml")
        if baseline is not None:
            state["tests_passed_before"] = len(baseline[0])
    try:
        source.write_bytes(proposed.read_bytes())
        # 파일(.pyc)을 만들지 않고 문법만 확인한다.
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
        # ⚠ test_paths가 비어 있으면 여기서 끝난다 = 문법만 맞으면 제안이 원본에 남는다.
        if test_paths:
            code, tail, after = _run_tests(root, test_paths, deadline, backup_dir / "junit_after.xml")
            state["test_returncode"] = code
            state["test_output_tail"] = tail
            if after is not None:
                state["tests_passed_after"] = len(after[0])
                state["tests_total"] = after[1]
            if code != 0:
                if policy != "improve":
                    raise RuntimeError("tests failed after applying the proposal")
                if baseline is None or after is None:
                    raise RuntimeError("tests failed and per-test results are unavailable")
                newly_failed = sorted(baseline[0] - after[0])
                state["newly_failed"] = newly_failed[:20]
                if newly_failed:
                    raise RuntimeError(f"proposal broke {len(newly_failed)} previously passing tests")
                if len(after[0]) <= len(baseline[0]):
                    raise RuntimeError("proposal did not increase the number of passing tests")
                state["partial"] = True  # 전부는 아니지만 통과 수가 늘고 퇴행이 없어 적용
        state["applied"] = True
    except Exception as error:  # 컴파일 오류·테스트 실패·시간 초과 모두 되돌린다
        source.write_bytes(original_bytes)
        state.update(rolled_back=True, reason=f"{type(error).__name__}: {error}"[:500])
    return state
