"""어느 AI(Gemini·ChatGPT·Claude·Ollama 등)가 만든 수정 코드든 받아 안전하게 적용하는 MCP 도구 (2026-11-10).

목적
    review_python_source는 Gemini 리뷰 결과만 자동 적용할 수 있었다.
    이 도구는 LLM 종류와 무관하게, 호출한 AI가 만든 "수정된 전체 소스"를 받아
    같은 안전 절차(검증 → 백업 → 적용 → 테스트 → 실패 시 되돌림)로 원본에 반영한다.
    실제 적용 로직은 재사용 모듈 harness.mcp.tools.auto_apply를 그대로 쓴다.

호출 예 (어느 MCP 클라이언트에서든)
    apply_source_proposal(source_path="FastAPI/x.py", proposed_source="<전체 수정 소스>",
                          test_paths=["tests/test_x.py"], expected_sha256="<source_read로 본 해시>",
                          dry_run=True)   # 먼저 검사만
    → 결과 확인 후 dry_run=False로 다시 호출하면 실제 적용

안전 장치
    - dry_run 기본값 True: 검사만 하고 원본·파일 시스템을 바꾸지 않는다.
    - 제안 소스 검사: 크기 상한, 문법(ast.parse), 생략 기호(...) 금지, 기존 최상위 함수·클래스 누락 금지,
      원본에 없던 "존재하지 않는 import/-m 모듈" 금지(review_contract와 같은 규칙).
    - expected_sha256을 주면, 그 사이 원본이 바뀐 경우 적용하지 않는다(다른 작업 보호).
    - 원본은 harness/memory/source_proposals/job_<id>/original.py에 백업된다.
    - Git 커밋은 하지 않는다(사람이 확인 후 지시).

⚠ 주의: test_paths 없이 호출하면 문법만 맞아도 원본이 바뀐다(동작이 달라져도 되돌리지 않음).
  중요한 파일은 반드시 test_paths=["tests/...", "harness/tests/..."]를 함께 넘길 것.
  이 도구는 MCP 요청 안에서 바로 pytest를 돌리므로, 테스트 시간은
  config.APPLY_PROPOSAL_TEST_TIMEOUT_SECONDS(짧게 유지)로 제한된다.
"""
from __future__ import annotations

import ast
import hashlib
import re
import sys
from pathlib import Path
from uuid import uuid4

import config as project_config
from common.common_function import logger, normalize_required_text
from FastAPI.LangGraph.multi_persona.review_contract import unresolved_imports
from harness.mcp.tools import auto_apply

PROJECT_ROOT = Path(project_config.PROJECT_ROOT).resolve()


def _project_source(value: str) -> Path:
    """프로젝트 안의 기존 .py 파일만 허용한다(심볼릭 링크까지 풀어서 확인)."""
    if not isinstance(value, str):
        raise ValueError("source_path must be text")
    path = (PROJECT_ROOT / Path(normalize_required_text(value, "source_path")).expanduser()).resolve()
    if PROJECT_ROOT not in path.parents:
        raise ValueError("source_path must stay inside the project")
    if path.suffix != ".py":
        raise ValueError("source_path must name a Python source")
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found: {value}")
    return path


def _check_proposal(original_text: str, proposed: str) -> list[str]:
    """제안 소스의 형식 오류를 모아 돌려준다(빈 목록이면 통과). 코드를 실행하지 않는다."""
    errors = []
    try:
        tree = ast.parse(proposed)
    except SyntaxError as error:
        return ["proposed_source syntax error: " + str(error.msg)]
    # LLM이 '...'로 코드를 생략한 불완전한 제안을 막는다.
    if any(isinstance(node, ast.Constant) and node.value is Ellipsis for node in ast.walk(tree)):
        errors.append("proposed_source contains an Ellipsis placeholder")
    try:
        old = ast.parse(original_text)
    except SyntaxError:
        old = None
    if old is not None:
        kinds = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        missing = ({n.name for n in old.body if isinstance(n, kinds)}
                   - {n.name for n in tree.body if isinstance(n, kinds)})
        if missing:
            errors.append("proposed_source drops existing symbols: " + ", ".join(sorted(missing)))
    # 원본에서는 해석되던 import/-m 모듈이 제안에서 사라진 이름으로 바뀌면 거부(2026-11-02 사고 재발 방지).
    missing_modules = unresolved_imports(tree, old, [PROJECT_ROOT, *sys.path])
    if missing_modules:
        errors.append("proposed_source imports missing modules: " + ", ".join(missing_modules))
    return errors


def apply_source_proposal(
    source_path: str,
    proposed_source: str,
    test_paths: list[str] | None = None,
    expected_sha256: str | None = None,
    dry_run: bool = True,
) -> dict:
    """Apply a full replacement Python source produced by any AI (Gemini, ChatGPT, Claude, Ollama).

    Default dry-run only validates the proposal and paths; nothing is written.
    With dry_run=False the original is backed up, the proposal is written, compiled,
    test_paths (inside tests/ or harness/tests/) run with pytest, and any failure restores the original.
    Pass expected_sha256 (from source_read) so a concurrently changed file is never overwritten.
    Without test_paths only the syntax check guards the change. No Git commit is made.
    """
    source = _project_source(source_path)
    if not isinstance(proposed_source, str) or not proposed_source.strip():
        raise ValueError("proposed_source must be non-empty text")
    if len(proposed_source) > int(project_config.APPLY_PROPOSAL_MAX_CHARS):
        raise ValueError("proposed_source exceeds the configured size limit")
    if expected_sha256 is not None and re.fullmatch(r"[0-9a-f]{64}", str(expected_sha256)) is None:
        raise ValueError("expected_sha256 must be a 64-character lowercase hex digest")
    tests = auto_apply.validate_test_paths(test_paths, PROJECT_ROOT)

    original_bytes = source.read_bytes()
    current_sha = hashlib.sha256(original_bytes).hexdigest()
    relative = str(source.relative_to(PROJECT_ROOT))
    errors = _check_proposal(original_bytes.decode("utf-8", errors="replace"), proposed_source)
    if expected_sha256 is not None and expected_sha256 != current_sha:
        errors.append("source changed since expected_sha256 was read")
    plan = {"dry_run": bool(dry_run), "source_path": relative, "source_sha256": current_sha,
            "test_paths": tests, "checks_passed": not errors, "errors": errors,
            "unchanged_proposal": proposed_source.encode("utf-8") == original_bytes}
    if dry_run or errors or plan["unchanged_proposal"]:
        plan["applied"] = False
        return plan

    # 실제 적용: 제안 소스를 job 폴더에 남기고 재사용 모듈로 백업·적용·검증·되돌림을 맡긴다.
    job_id = uuid4().hex
    job_dir = PROJECT_ROOT / "harness/memory/source_proposals" / ("job_" + job_id)
    job_dir.mkdir(parents=True, mode=0o700)
    proposed_path = job_dir / "proposed.py"
    proposed_path.write_text(proposed_source, encoding="utf-8")
    proposed_path.chmod(0o600)
    timeout = int(project_config.APPLY_PROPOSAL_TEST_TIMEOUT_SECONDS)
    state = auto_apply.apply_with_rollback(
        source, proposed_path, job_dir, current_sha, tests,
        budget=timeout + 10,  # apply_with_rollback은 결과 여유 10초를 빼고 pytest 시간을 정한다
        project_root=PROJECT_ROOT)
    logger.info("apply_source_proposal: job=%s source=%s applied=%s rolled_back=%s",
                job_id, relative, state.get("applied"), state.get("rolled_back"))
    return {**plan, "job_id": job_id, "proposed_path": str(proposed_path.relative_to(PROJECT_ROOT)),
            **state}
