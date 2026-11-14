"""수집 에이전트의 한 파일 수정을 재현 테스트로 검증하고 원본을 보존한다.

LangChain 도구는 이 모듈을 호출하며 기존 LangGraph 노드/엣지는 유지한다.
테스트는 임시 후보 파일에 대해 실행한다. 프로세스 분리는 보안 샌드박스가
아니므로 신뢰된 프로젝트 작업에만 사용하며 설정/인증/검증기 자체는 수정하지 않는다.

2026-10-25 LuckyBoys: "source_repair.py 자체도 LangGraph로" → repair_source의 단계를 StateGraph로 실행한다.
(원본: haness/source_repair_BACKUP_20261025_215433.py — 판정·백업·원복·git add 규칙은 그대로)
    START → baseline(원본에서 재현 실패 확인, 아니면 ValueError)
          → candidate(후보 dry-run/실행/dry-run 3회 검증)
          ─(실패 또는 dry_run)→ END
          ─(통과·실행)→ apply(해시·Git 기준 재확인 → 백업 → 감사 PREPARED → 쓰기 → 재검증, 실패 시 원복·예외)
          → stage(git add까지만, 커밋 안 함 — 감사 기록 실패 시 원복·예외) → END
    노드에서 난 예외는 graph.invoke 밖으로 그대로 나온다(호출자 계약 유지).
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
from typing import TypedDict
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


def _stage_only(target: Path) -> dict:
    """검증을 통과해 적용된 자율 수정을 git add까지만 한다(커밋은 사람이 git diff --cached 확인 후).

    2026-10-25 LuckyBoys: "자동 커밋 → git add까지만". 예전 _auto_commit(PARTNER 이름 자동 커밋)을 대체한다.
    (원본은 haness/source_repair_BACKUP_20261025_210602.py에 보존)
    입력: target(적용된 파일의 절대경로) / 출력: {"staged": bool, "error": <실패 사유, 성공 시 없음>}
    주의: 이미 적용된 패치를 롤백하지 않도록 예외를 던지지 않는다. add가 실패하면 워킹트리 변경만 남고,
    다음 수정은 _git_checkpoint의 PreCommitRequired로 막힌다(기존 안전장치 유지).
    """
    root = _root()
    relative = str(target.relative_to(root))
    try:
        add = subprocess.run(["git", "add", "--", relative], cwd=root, capture_output=True,
                             timeout=config.SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS)
    except (subprocess.TimeoutExpired, OSError) as error:
        return {"staged": False, "error": type(error).__name__}
    if add.returncode:
        return {"staged": False, "error": "git add 실패"}
    return {"staged": True}


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
            # -B: 바이트코드(.pyc)를 쓰지 않는다. 같은 초·같은 크기로 후보를 바꾸면 이전 .pyc가 재사용되어
            # 원본 코드로 테스트되는 문제가 있었다(2026-10-25 재현 테스트로 확인: a-b → a+b 교체가 실패로 판정).
            [sys.executable, "-I", "-B", "-c", runner, str(test_file), str(candidate),
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
    git add까지만 한다(2026-10-25 변경: 자동 커밋 안 함 — 사람이 git diff --cached 확인 후 커밋).
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
            # 그래프 상태: 노드 사이에 넘기는 값. 임시 폴더·락은 invoke 동안 이 함수가 유지한다.
            state = {"file_path": file_path, "target": target, "original": original,
                     "candidate_text": candidate_text, "regression_test": regression_test,
                     "before": before, "checkpoint": checkpoint, "dry_run": dry_run,
                     "lock_dir": lock_dir, "candidate": temp / target.name,
                     "test_file": temp / "regression_test.py", "report": {}}
            return build_repair_graph().invoke(state)["report"]


# ---------------------------------------------------------------------------
# LangGraph: 재현 → 후보 검증 → 적용 → git add (2026-10-25)
# ---------------------------------------------------------------------------
# repair_source 그래프 상태. 노드는 바뀐 키만 돌려준다.
# 함수형 TypedDict를 쓰는 이유: 이 파일은 `from __future__ import annotations`라 class 문법의 타입이 문자열로 남는데,
# 모듈을 spec_from_file_location으로 읽으면(sys.modules 미등록) LangGraph의 get_type_hints가 문자열을 풀지 못한다.
RepairState = TypedDict("RepairState", {
    "file_path": str,         # 프로젝트 상대 경로(허용 목록 검사 완료)
    "target": Path,           # 실제 대상 파일
    "original": bytes,        # 수정 전 원본 바이트(원복 기준)
    "candidate_text": str,    # old_code→new_code 1회 교체 결과
    "regression_test": str,   # 재현 unittest 원문
    "before": str,            # 원본 sha256
    "checkpoint": dict,       # _git_checkpoint 결과(적용 직전 재확인용)
    "dry_run": bool,
    "lock_dir": Path,         # 감사 파일·락 폴더(config.SPS_SOURCE_REPAIR_AUDIT_DIR)
    "candidate": Path,        # 임시 폴더의 후보 파일
    "test_file": Path,        # 임시 폴더의 재현 테스트 파일
    "baseline": dict,         # 원본 대상 테스트 결과(실패해야 재현)
    "report": dict,           # 호출자에게 돌려줄 보고서
    "backup": Path,           # 적용 전 원본 백업
    "audit": Path,            # 감사 JSON
}, total=False)


def _write_audit(audit: Path, report: dict) -> None:
    """감사 파일을 현재 보고서로 덮어쓴다(PREPARED → APPLIED → git_stage / ROLLED_BACK)."""
    audit.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _rollback(state: RepairState, report: dict) -> None:
    """적용·stage 단계 실패 시 원본 바이트로 되돌리고 감사에 ROLLED_BACK을 남긴다(예외는 호출 노드가 다시 던짐)."""
    _atomic_write(state["target"], state["original"], state["backup"].stat().st_mode & 0o777)
    report.update(success=False, applied=False, state="ROLLED_BACK")
    _write_audit(state["audit"], report)


def _node_baseline(state: RepairState) -> dict:
    """원본으로 재현 테스트를 돌린다. 통과·0개·인프라 오류면 재현이 아니므로 ValueError(수정하지 않음)."""
    state["test_file"].write_text(state["regression_test"], encoding="utf-8")
    state["candidate"].write_bytes(state["original"])
    baseline = _check(state["candidate"], state["test_file"], False)
    if baseline.get("infrastructure_error") or baseline.get("tests", 0) < 1 or baseline["passed"]:
        raise ValueError("기존 소스에서 오류가 재현되는 회귀 테스트가 필요합니다")
    return {"baseline": baseline}


def _node_candidate(state: RepairState) -> dict:
    """후보를 dry-run/실행/dry-run 3회 검증한다(지침 7: dry-run 전후 통과). 실패하면 success False 보고."""
    state["candidate"].write_text(state["candidate_text"], encoding="utf-8")
    checks = [_check(state["candidate"], state["test_file"], mode) for mode in (True, False, True)]
    if not all(item["passed"] for item in checks):
        return {"report": {"success": False, "applied": False, "checks": checks}}
    after = hashlib.sha256(state["candidate"].read_bytes()).hexdigest()
    return {"report": {"success": True, "applied": False, "dry_run": state["dry_run"],
                       "path": state["file_path"], "before_sha256": state["before"], "after_sha256": after,
                       "baseline": state["baseline"], "checks": checks, "git_checkpoint": state["checkpoint"]}}


def _route_after_candidate(state: RepairState) -> str:
    """후보 실패 또는 dry_run이면 여기서 끝(원본 쓰지 않음), 아니면 적용."""
    return "apply" if state["report"].get("success") and not state["dry_run"] else "end"


def _node_apply(state: RepairState) -> dict:
    """적용 직전 재확인 → 백업(xb, 덮어쓰기 금지) → 감사 PREPARED → 원자적 쓰기 → 재검증. 실패 시 원복 후 예외."""
    target, original, report = state["target"], state["original"], dict(state["report"])
    if target.read_bytes() != original:
        raise ValueError("검증 중 원본 변경 감지")
    if _git_checkpoint(target) != state["checkpoint"]:
        raise PreCommitRequired("검증 중 Git 기준 커밋 변경 감지")
    stamp = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d_%H%M%S_%f")
    backup = target.with_name(target.stem + "_BACKUP_" + stamp + target.suffix)
    # 원본 바이트를 배타적으로 저장하며 기존 백업을 덮어쓰지 않는다.
    with backup.open("xb") as stream:
        stream.write(original)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(backup, target.stat().st_mode & 0o777)
    audit = state["lock_dir"] / ("repair_" + stamp + ".json")
    report.update(backup=str(backup.relative_to(_root())), state="PREPARED")
    _write_audit(audit, report)
    try:
        _atomic_write(target, state["candidate_text"].encode("utf-8"), target.stat().st_mode & 0o777)
        post = [_check(target, state["test_file"], mode) for mode in (True, False, True)]
        if not all(item["passed"] for item in post):
            raise RuntimeError("적용 후 회귀 테스트 실패")
        if hashlib.sha256(target.read_bytes()).hexdigest() != report["after_sha256"]:
            raise RuntimeError("적용 후 해시 검증 실패")
        report.update(applied=True, state="APPLIED", post_checks=post, restart_required=True)
        _write_audit(audit, report)
    except BaseException:
        _rollback({**state, "backup": backup, "audit": audit}, report)
        raise
    return {"report": report, "backup": backup, "audit": audit}


def _node_stage(state: RepairState) -> dict:
    """git add까지만 한다(커밋 안 함). 근거(백업·테스트 수)는 감사 파일에 남는다. 감사 기록 실패 시 원복."""
    report = dict(state["report"])
    try:
        report["git_stage"] = _stage_only(state["target"])
        _write_audit(state["audit"], report)
    except BaseException:
        _rollback(state, report)
        raise
    return {"report": report}


def build_repair_graph():
    """repair_source 단계를 LangGraph StateGraph로 조립해 compile()한 그래프를 돌려준다."""
    from langgraph.graph import END, START, StateGraph   # 지연 import: read_repair_source만 쓸 때는 불필요

    graph = StateGraph(RepairState)
    graph.add_node("baseline", _node_baseline)
    graph.add_node("candidate", _node_candidate)
    graph.add_node("apply", _node_apply)
    graph.add_node("stage", _node_stage)
    graph.add_edge(START, "baseline")
    graph.add_edge("baseline", "candidate")
    graph.add_conditional_edges("candidate", _route_after_candidate, {"apply": "apply", "end": END})
    graph.add_edge("apply", "stage")
    graph.add_edge("stage", END)
    return graph.compile()
