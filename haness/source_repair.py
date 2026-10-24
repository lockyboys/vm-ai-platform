"""수집 에이전트의 한 파일 수정을 재현 테스트로 검증하고 원본을 보존한다.

LangChain 도구는 이 모듈을 호출하며 기존 LangGraph 노드/엣지는 유지한다.
테스트는 임시 후보 파일에 대해 실행한다. 프로세스 분리는 보안 샌드박스가
아니므로 신뢰된 프로젝트 작업에만 사용하며 설정/인증/검증기 자체는 수정하지 않는다.
"""
from __future__ import annotations

import ast
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config
from common.common_function import normalize_required_text


class PreCommitRequired(ValueError):
    """수정 대상의 현재 내용이 Git에 보존되지 않아 자동 수정을 중단한다."""


def _git_checkpoint(target: Path) -> dict:
    """대상 파일이 현재 HEAD와 일치하며 staged 변경도 없는지 확인한다.

    커밋을 만들거나 stage를 변경하지 않는다. 다른 파일의 변경은 건드리지 않는다.
    미커밋 원본을 백업만 한 채 덮어쓰는 일이 없도록 dry-run에서도 검사한다.
    """
    root = _root()
    relative = str(target.relative_to(root))
    def git(*arguments):
        try:
            return subprocess.run(["git", *arguments], cwd=root, capture_output=True,
                                  timeout=config.SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS)
        except (subprocess.TimeoutExpired, OSError) as error:
            raise PreCommitRequired("Git 커밋 상태를 확인하지 못했습니다") from error
    top = git("rev-parse", "--show-toplevel")
    if top.returncode or Path(os.fsdecode(top.stdout).strip()).resolve() != root:
        raise PreCommitRequired("프로젝트 Git 저장소 확인 필요")
    head = git("rev-parse", "--verify", "HEAD")
    committed = git("show", "HEAD:" + relative)
    staged = git("diff", "--cached", "--quiet", "--", relative)
    if head.returncode or committed.returncode or staged.returncode:
        raise PreCommitRequired("수정 대상의 사전 커밋이 필요합니다")
    if committed.stdout != target.read_bytes():
        raise PreCommitRequired("미커밋 변경이 있어 자율 수정을 중단합니다")
    return {"ready": True, "commit": head.stdout.decode("ascii").strip()}


def _auto_commit(target: Path, message: str, agent_run_id: str) -> dict:
    """검증을 통과해 적용된 자율 수정을 사람의 git add/commit 없이 자동으로 커밋한다.

    입력: target(커밋할 파일의 절대경로), message(커밋 메시지, 한글, 태그·백업 경로·테스트
    통과 수 포함), agent_run_id(이번 실행을 식별하는 ID — 백업·감사 로그 파일명과 같은 값을
    재사용해 셋을 서로 추적 가능하게 한다)
    출력: {"committed": bool, "commit": <새 HEAD sha, 실패 시 None>, "error": <실패 사유, 성공 시 없음>}
    주의: 이미 디스크에 적용된 패치를 롤백하지 않기 위해 예외를 던지지 않는다.
    커밋이 실패하면 워킹트리가 깨끗하지 않은 상태로 남아, 다음 수정 시도는 기존과 동일하게
    _git_checkpoint의 PreCommitRequired로 막힌다(기존 안전장치 유지).
    author/committer를 SPS ORCHESTRATOR의 PARTNER 페르소나(코드 구현·제출 담당) 이름으로
    지정해, git log 작성자 칼럼만 보고도 사람 커밋과 AI 자동 커밋이 구분되고 어느 페르소나가
    했는지도 드러나게 한다. 이메일 local-part에 agent_run_id를 넣어 실행 단위까지 구분한다.
    """
    root = _root()
    relative = str(target.relative_to(root))
    bot_name = "SPS PARTNER"
    bot_email = f"sps.partner+{agent_run_id}@sps.local"
    bot_identity = f"{bot_name} <{bot_email}>"
    git_env = {**os.environ,
               "GIT_AUTHOR_NAME": bot_name,
               "GIT_AUTHOR_EMAIL": bot_email,
               "GIT_COMMITTER_NAME": bot_name,
               "GIT_COMMITTER_EMAIL": bot_email}
    try:
        add = subprocess.run(["git", "add", "--", relative], cwd=root, capture_output=True,
                              timeout=config.SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS)
        if add.returncode:
            return {"committed": False, "commit": None, "error": "git add 실패"}
        commit = subprocess.run(
            ["git", "commit", "--author", bot_identity, "-m", message, "--", relative],
            cwd=root, capture_output=True, env=git_env,
            timeout=config.SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS,
        )
        if commit.returncode:
            return {"committed": False, "commit": None, "error": "git commit 실패"}
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                              timeout=config.SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS)
        return {"committed": True,
                "commit": sha.stdout.decode("ascii").strip() if sha.returncode == 0 else None}
    except (subprocess.TimeoutExpired, OSError) as error:
        return {"committed": False, "commit": None, "error": type(error).__name__}


def _root() -> Path:
    return Path(config.BASE_DIR).resolve()


def _target(file_path: str) -> Path:
    """프로젝트 상대 경로와 명시적 허용 목록을 모두 검사한다."""
    value = normalize_required_text(file_path, "file_path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("프로젝트 상대 경로만 허용합니다")
    if relative.as_posix() not in config.SPS_SOURCE_REPAIR_ALLOWED_PATHS:
        raise ValueError("자동 수정 허용 목록에 없는 파일입니다")
    root = _root()
    target = root / relative
    if target.is_symlink() or target.resolve() != target or not target.is_file():
        raise ValueError("실제 프로젝트 파일만 허용합니다")
    if not target.resolve().is_relative_to(root):
        raise ValueError("프로젝트 밖 파일입니다")
    return target


def read_repair_source(file_path: str) -> dict:
    """에이전트가 수정 전 파일과 해시를 읽게 한다. 인증 설정은 허용하지 않는다."""
    target = _target(file_path)
    raw = target.read_bytes()
    if len(raw) > config.SPS_SOURCE_REPAIR_MAX_BYTES:
        raise ValueError("소스 크기 제한 초과")
    try:
        checkpoint = _git_checkpoint(target)
    except PreCommitRequired:
        checkpoint = {"ready": False, "error_code": "PRE_COMMIT_REQUIRED"}
    return {"path": file_path, "sha256": hashlib.sha256(raw).hexdigest(),
            "source": raw.decode("utf-8"), "git_checkpoint": checkpoint}


def _check(candidate: Path, test_file: Path, dry_run: bool) -> dict:
    """셸 없이 고정 테스트 실행기를 호출하며 테스트 0개/skip은 실패로 처리한다.

    회귀 테스트는 SOURCE_PATH의 후보를 대상으로 unittest.TestCase를 정의한다.
    후보를 import할 때 부작용이 있으면 AST로 대상 함수를 분리하여 테스트한다.
    테스트 stdout/stderr는 인증정보가 섞일 수 있어 보고에 포함하지 않는다.
    """
    runner = '''import os, runpy, sys, unittest
namespace = runpy.run_path(sys.argv[1], init_globals={
    "SOURCE_PATH": sys.argv[2], "DRY_RUN": sys.argv[3] == "1"})
suite = unittest.TestSuite()
for name, value in namespace.items():
    if isinstance(value, type) and issubclass(value, unittest.TestCase):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(value))
result = unittest.TestResult()
suite.run(result)
ok = result.testsRun > 0 and result.wasSuccessful() and not result.skipped
print(__import__("json").dumps({"passed": ok, "tests": result.testsRun,
    "failures": len(result.failures), "errors": len(result.errors)}))
sys.exit(0 if ok else 1)
'''
    try:
        # 인증 환경변수는 넘기지 않는다. OS 접근을 격리하는 보안 샌드박스는 아니다.
        result = subprocess.run(
            [sys.executable, "-I", "-c", runner, str(test_file), str(candidate),
             "1" if dry_run else "0"], cwd=candidate.parent,
            env={"PATH": os.defpath, "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True,
            timeout=config.SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS)
        summary = json.loads(result.stdout.strip().splitlines()[-1])
        return {**summary, "passed": result.returncode == 0 and summary.get("passed") is True}
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        return {"passed": False, "tests": 0, "infrastructure_error": True}


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    """같은 디렉터리에서 fsync 후 교체하여 부분 파일이 남지 않게 한다."""
    fd, name = tempfile.mkstemp(prefix=".repair_", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def repair_source(file_path: str, old_code: str, new_code: str,
                  regression_test: str, expected_sha256: str,
                  dry_run: bool = True) -> dict:
    """수정 전 재현 실패/후보 통과를 확인하고 백업 후 한 파일에만 적용한다.

    dry_run=True도 후보의 회귀 테스트를 실행하지만 원본은 쓰지 않는다.
    실행 직후 재검증이 실패하면 원본 바이트로 복구한다. 검증을 통과해 적용되면
    사람의 git add/commit 없이 바로 커밋한다(사전 승인 없는 사후 보고 방식).
    소스 교체는 이미 로드된 Python 객체를 바꾸지 않으므로 새 워커가 필요하다.
    """
    target = _target(file_path)
    checkpoint = _git_checkpoint(target)
    if not isinstance(dry_run, bool):
        raise ValueError("dry_run은 bool이어야 합니다")
    for label, value in (("old_code", old_code), ("new_code", new_code),
                         ("regression_test", regression_test)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(label + "는 비어 있지 않은 문자열이어야 합니다")
        if len(value.encode("utf-8")) > config.SPS_SOURCE_REPAIR_MAX_BYTES:
            raise ValueError(label + " 크기 제한 초과")
    if old_code == new_code:
        raise ValueError("변경 내용이 없습니다")
    lock_dir = _root() / config.SPS_SOURCE_REPAIR_AUDIT_DIR
    lock_dir.mkdir(parents=True, exist_ok=True)
    # 모든 수정을 직렬화하고 실행 중 소스의 해시가 바뀌면 덮어쓰지 않는다.
    with (lock_dir / "repair.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original = target.read_bytes()
        before = hashlib.sha256(original).hexdigest()
        if before != expected_sha256:
            raise ValueError("원본 해시가 달라졌습니다. 다시 읽어 주세요")
        source = original.decode("utf-8")
        if source.count(old_code) != 1:
            raise ValueError("수정 위치는 정확히 한 곳이어야 합니다")
        candidate_text = source.replace(old_code, new_code, 1)
        if len(candidate_text.encode("utf-8")) > config.SPS_SOURCE_REPAIR_MAX_BYTES:
            raise ValueError("후보 소스 크기 제한 초과")
        ast.parse(candidate_text, filename=file_path)
        ast.parse(regression_test, filename="regression_test.py")
        with tempfile.TemporaryDirectory(prefix="sps_repair_") as directory:
            temp = Path(directory)
            candidate = temp / target.name
            test_file = temp / "regression_test.py"
            test_file.write_text(regression_test, encoding="utf-8")
            candidate.write_bytes(original)
            baseline = _check(candidate, test_file, False)
            if baseline.get("infrastructure_error") or baseline.get("tests", 0) < 1 or baseline["passed"]:
                raise ValueError("기존 소스에서 오류가 재현되는 회귀 테스트가 필요합니다")
            candidate.write_text(candidate_text, encoding="utf-8")
            checks = [_check(candidate, test_file, mode) for mode in (True, False, True)]
            if not all(item["passed"] for item in checks):
                return {"success": False, "applied": False, "checks": checks}
            after = hashlib.sha256(candidate.read_bytes()).hexdigest()
            report = {"success": True, "applied": False, "dry_run": dry_run,
                      "path": file_path, "before_sha256": before, "after_sha256": after,
                      "baseline": baseline, "checks": checks,
                      "git_checkpoint": checkpoint}
            if dry_run:
                return report
            if target.read_bytes() != original:
                raise ValueError("검증 중 원본 변경 감지")
            if _git_checkpoint(target) != checkpoint:
                raise PreCommitRequired("검증 중 Git 기준 커밋 변경 감지")
            stamp = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d_%H%M%S_%f")
            backup = target.with_name(target.stem + "_BACKUP_" + stamp + target.suffix)
            # 원본 바이트를 배타적으로 저장하며 기존 백업을 덮어쓰지 않는다.
            with backup.open("xb") as stream:
                stream.write(original)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(backup, target.stat().st_mode & 0o777)
            audit = lock_dir / ("repair_" + stamp + ".json")
            report.update(backup=str(backup.relative_to(_root())), state="PREPARED")
            audit.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                _atomic_write(target, candidate_text.encode("utf-8"), target.stat().st_mode & 0o777)
                post = [_check(target, test_file, mode) for mode in (True, False, True)]
                if not all(item["passed"] for item in post):
                    raise RuntimeError("적용 후 회귀 테스트 실패")
                if hashlib.sha256(target.read_bytes()).hexdigest() != after:
                    raise RuntimeError("적용 후 해시 검증 실패")
                report.update(applied=True, state="APPLIED", post_checks=post,
                              restart_required=True)
                audit.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                # 사람의 git add/commit을 기다리지 않고 바로 커밋한다(사후 보고 방식).
                # 메시지는 한글로, 작성자는 PARTNER 페르소나로 남겨 git log/revert로 나중에 검토할 수 있게 한다.
                commit_message = (
                    f"[SPS 자동수정] {file_path} 패치 적용\n\n"
                    f"백업 파일: {report['backup']}\n"
                    f"통과한 회귀 테스트 수: {post[-1].get('tests', 0)}\n"
                    f"에이전트 실행 ID: {stamp}"
                )
                report["git_commit"] = _auto_commit(target, commit_message, stamp)
                audit.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            except BaseException:
                _atomic_write(target, original, backup.stat().st_mode & 0o777)
                report.update(success=False, applied=False, state="ROLLED_BACK")
                audit.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                raise
            return report
