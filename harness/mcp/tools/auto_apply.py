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

함수 단위 되돌림(2026-11-21, LuckyBoys 승인 '추가 기능 차단')
    - improve 규칙에서 제안이 퇴행(원래 통과하던 테스트 실패)을 내면, 바로 전부 되돌리지 않고
      제안에서 바뀐 '맨 바깥 함수·클래스'를 하나씩 원본으로 되돌려 테스트해 본다.
    - 점수(퇴행 수가 적을수록, 같으면 통과 수가 많을수록)가 나빠지지 않는 되돌림만 남긴다.
    - 마지막에 위 improve 판정(퇴행 0 + 통과 수 증가)을 그대로 적용한다 = 판정 기준은 완화하지 않는다.
    - 최대 시도 개수는 config.MULTI_PERSONA_AUTO_APPLY_REVERT_MAX_FUNCTIONS(0 이하·숫자 아님이면 끔).
    - 사고 사례: 메모리 에이전트 시험에서 작은 모델이 결함과 무관한 Gmail·검증 노드까지 바꿔 매번 전부 되돌려졌다.

⚠ 주의: test_paths 없이 호출하면 문법만 맞아도 원본이 바뀐다(동작이 달라져도 되돌리지 않음).
  중요한 파일은 반드시 test_paths=["tests/...", "harness/tests/..."]를 함께 넘길 것.
  허용 폴더와 pytest 시간 상한은 루트 config.py에서 읽는다(일반 지침 4, 하드코딩 금지):
    - MULTI_PERSONA_AUTO_APPLY_TEST_ROOTS
    - MULTI_PERSONA_AUTO_APPLY_TEST_TIMEOUT_SECONDS
    - MULTI_PERSONA_AUTO_APPLY_POLICY
"""
from __future__ import annotations

import ast
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


# ---------------------------------------------------------------------------
# 2026-11-21 함수 단위 되돌림(추가 기능 차단) — 아래 함수들은 apply_with_rollback 안에서만 쓴다.
# ---------------------------------------------------------------------------
def _revert_limit() -> int:
    """되돌려 볼 함수·클래스 최대 개수. 설정이 없거나 0 이하·bool·숫자 아님이면 0(= 기능 끔)."""
    value = getattr(project_config, "MULTI_PERSONA_AUTO_APPLY_REVERT_MAX_FUNCTIONS", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return 0
    return value


def _top_level_defs(text: str) -> dict:
    """맨 바깥 함수·클래스 이름 → (시작 줄, 끝 줄). 줄 번호는 1부터, 데코레이터 줄을 포함한다.

    문법 오류면 빈 dict(되돌림 대상 없음). 같은 이름이 두 번 나오면 뒤의 것을 쓴다(파이썬 실행 결과와 같음).
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    spans = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = min([node.lineno] + [item.lineno for item in node.decorator_list])
            spans[node.name] = (start, node.end_lineno)
    return spans


def _segment(lines: list, span: tuple) -> str:
    """줄 목록에서 (시작, 끝) 줄 구간 문자열(끝 줄 포함)."""
    return "".join(lines[span[0] - 1:span[1]])


def _changed_defs(original: str, proposal: str) -> list:
    """원본과 제안 양쪽에 있는데 내용이 달라진 맨 바깥 함수·클래스 이름(제안에서 위에 있는 순서).

    제안에만 있는 새 함수(도우미)·원본에만 있는 함수는 대상이 아니다(되돌릴 원본 짝이 없거나 이미 빠짐).
    """
    old, new = _top_level_defs(original), _top_level_defs(proposal)
    old_lines, new_lines = original.splitlines(keepends=True), proposal.splitlines(keepends=True)
    changed = [name for name in new
               if name in old and _segment(new_lines, new[name]) != _segment(old_lines, old[name])]
    return sorted(changed, key=lambda name: new[name][0])


def _revert_def(current: str, original: str, name: str):
    """current 소스에서 name 함수·클래스만 원본 내용으로 바꾼 소스. 어느 한쪽에 없으면 None."""
    now, old = _top_level_defs(current), _top_level_defs(original)
    if name not in now or name not in old:
        return None
    lines = current.splitlines(keepends=True)
    piece = _segment(original.splitlines(keepends=True), old[name])
    if not piece.endswith("\n"):
        piece += "\n"  # 원본에서 파일 끝 줄이었으면 줄바꿈이 없으므로 다음 줄과 붙지 않게 넣는다
    start, end = now[name]
    return "".join(lines[:start - 1]) + piece + "".join(lines[end:])


def _score(baseline_passed: set, passed: set) -> tuple:
    """좋음의 순서: 퇴행(기준선에서 통과→실패) 수가 적을수록, 같으면 통과 수가 많을수록 좋다."""
    return (-len(baseline_passed - passed), len(passed))


def _salvage_by_function_revert(root: Path, source: Path, original: str, proposal: str,
                                test_paths: list, deadline: float, backup_dir: Path,
                                baseline: tuple, after: tuple):
    """퇴행을 낸 제안에서 바뀐 함수·클래스를 하나씩 원본으로 되돌려 보고, 점수가 나빠지지 않는 것만 남긴다.

    반환: (최종 소스 문자열, 최종 (통과 집합, 전체 수), 되돌린 이름 목록) / 시도할 것이 없으면 None.
    최종 소스는 source 파일에도 써 둔다(호출자가 판정 후 유지하거나 백업으로 되돌린다).
    점수가 같아도 되돌리는 이유: 같은 결과라면 원본에 더 가까운 쪽이 '최소 수정'이다.
    """
    limit = _revert_limit()
    names = _changed_defs(original, proposal)[:limit] if limit else []
    if not names:
        return None
    current, best, reverted = proposal, after, []
    trial_xml = backup_dir / "junit_revert.xml"
    for name in names:
        if deadline - time.monotonic() < 30:      # 결과 저장·되돌림 여유(apply_with_rollback의 최소 예산과 같은 30초)
            break
        candidate = _revert_def(current, original, name)
        if candidate is None:
            continue
        try:
            compile(candidate, str(source), "exec")
        except SyntaxError:
            continue                               # 이어 붙인 결과가 문법 오류면 이 되돌림은 건너뜀
        source.write_text(candidate, encoding="utf-8")
        _code, _tail, trial = _run_tests(root, test_paths, deadline, trial_xml)
        if trial is None:
            continue                               # 결과를 못 읽으면 판단 근거가 없으므로 채택하지 않음
        if _score(baseline[0], trial[0]) >= _score(baseline[0], best[0]):
            current, best = candidate, trial
            reverted.append(name)
            shutil.copy2(trial_xml, backup_dir / "junit_salvaged.xml")  # 채택한 상태의 테스트 결과 기록
    source.write_text(current, encoding="utf-8")
    return current, best, reverted


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
                salvaged = False
                if newly_failed:
                    # 2026-11-21: 퇴행이 있으면 바뀐 함수·클래스를 하나씩 원본으로 되돌려 본다(판정 기준은 아래 그대로).
                    salvage = _salvage_by_function_revert(
                        root, source, original_bytes.decode("utf-8"), proposed.read_text(encoding="utf-8"),
                        test_paths, deadline, backup_dir, baseline, after)
                    if salvage is not None:
                        _final, after, reverted = salvage
                        newly_failed = sorted(baseline[0] - after[0])
                        salvaged = bool(reverted)
                        state.update(reverted_functions=reverted, newly_failed=newly_failed[:20],
                                     tests_passed_after=len(after[0]), tests_total=after[1])
                if newly_failed:
                    raise RuntimeError(f"proposal broke {len(newly_failed)} previously passing tests")
                if len(after[0]) <= len(baseline[0]):
                    raise RuntimeError("proposal did not increase the number of passing tests")
                # 전부는 아니지만 통과 수가 늘고 퇴행이 없어 적용. 되돌림 후 전부 통과했으면 부분 적용이 아니다.
                state["partial"] = (len(after[0]) < after[1]) if salvaged else True
                if salvaged and not state["partial"]:
                    state["test_returncode"] = 0
        state["applied"] = True
    except Exception as error:  # 컴파일 오류·테스트 실패·시간 초과 모두 되돌린다
        source.write_bytes(original_bytes)
        state.update(rolled_back=True, reason=f"{type(error).__name__}: {error}"[:500])
    return state
