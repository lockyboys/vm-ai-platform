"""LangChain 도구와 LangGraph로 SPS 소스 변경 세트를 안전하게 실행한다."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import PurePosixPath
from typing import Any, TypedDict

from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph

from haness.mcp.tools.multi_persona_tools import PROJECT_ROOT
from harness.mcp.tools.git_mutation_tools import git_add, git_commit
from harness.mcp.tools.patch_tools import source_patch
from harness.mcp.tools.pytest_tools import run_pytest_verification
from harness.mcp.tools.write_tools import (
    DENIED_FILE_NAMES,
    DENIED_SUFFIXES,
    EXCLUDED_DIRECTORY_NAMES,
    MAX_WRITE_BYTES,
    source_write,
)


_STAGE_GROUP_NAMES = ("source", "tests", "docs", "operations")
_CHANGE_SET_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class ChangeSetState(TypedDict, total=False):
    """그래프 노드가 공유하는 변경 세트 실행 상태."""

    request: dict[str, Any]
    change_set_id: str
    dry_run: bool
    patch_text: str
    test_paths: list[str]
    stage_groups: dict[str, list[str]]
    writes: list[dict[str, Any]]
    source_write_confirmed: bool
    write_backups: dict[str, dict[str, Any]]
    write_results: list[dict[str, Any]]
    commit: dict[str, Any]
    commit_state: str
    commit_result: dict[str, Any]
    activation: dict[str, Any]
    patch_plan: dict[str, Any]
    test_result: dict[str, Any]
    staged_groups: dict[str, list[str]]
    state: str
    success: bool
    evidence_path: str


def _clean_project_path(value: Any, field_name: str) -> str:
    """프로젝트 상대 경로만 허용해 절대 경로와 상위 디렉터리 이탈을 차단한다."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must contain non-empty project-relative paths")
    normalized = value.strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or normalized.startswith("/"):
        raise ValueError(f"{field_name} contains an unsafe path: {value}")
    return normalized


def _validate_write_request(value: Any, index: int) -> dict[str, Any]:
    """source_write의 승인 전에 경로·크기·옵션을 검증하고 내용을 변경하지 않는다."""
    if not isinstance(value, dict):
        raise ValueError(f"writes[{index}] must be an object")
    path = _clean_project_path(value.get("path"), f"writes[{index}].path")
    relative = PurePosixPath(path)
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative.parts):
        raise ValueError(f"writes[{index}].path uses an excluded directory")
    if relative.name in DENIED_FILE_NAMES or relative.suffix.lower() in DENIED_SUFFIXES:
        raise ValueError(f"writes[{index}].path is not allowed")
    content = value.get("content")
    if not isinstance(content, str):
        raise ValueError(f"writes[{index}].content must be text")
    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        raise ValueError(f"writes[{index}].content exceeds the write limit")
    overwrite = value.get("overwrite", False)
    create_parent = value.get("create_parent", True)
    if not isinstance(overwrite, bool) or not isinstance(create_parent, bool):
        raise ValueError(f"writes[{index}] options must be boolean")
    return {
        "path": path,
        "content": content,
        "overwrite": overwrite,
        "create_parent": create_parent,
    }


def _validate_request(payload: dict[str, Any], dry_run: bool) -> ChangeSetState:
    """외부 효과를 시작하기 전에 변경 세트 전체 계약을 한 번에 검증한다."""
    if not isinstance(payload, dict) or payload.get("mode") != "change_set":
        raise ValueError("mode must be change_set")

    change_set_id = payload.get("change_set_id")
    if not isinstance(change_set_id, str) or not _CHANGE_SET_ID.fullmatch(change_set_id):
        raise ValueError("change_set_id must be a safe identifier")

    raw_writes = payload.get("writes", [])
    if not isinstance(raw_writes, list):
        raise ValueError("writes must be a list")
    writes = [_validate_write_request(value, index) for index, value in enumerate(raw_writes)]
    write_paths = [value["path"] for value in writes]
    if len(write_paths) != len(set(write_paths)):
        raise ValueError("writes paths must be unique")
    source_write_confirmed = payload.get("source_write_confirmed", False)
    if not isinstance(source_write_confirmed, bool):
        raise ValueError("source_write_confirmed must be boolean")
    if writes and not dry_run and not source_write_confirmed:
        raise ValueError("source_write_confirmed=true is required before source_write")

    patch_text = payload.get("patch_text", "")
    if not isinstance(patch_text, str) or (not patch_text.strip() and not writes):
        raise ValueError("patch_text or writes must contain a source change")

    commit = payload.get(
        "commit", {"requested": False, "confirmed": False, "message": ""}
    )
    if not isinstance(commit, dict):
        raise ValueError("commit must be an object")
    if not isinstance(commit.get("requested", False), bool) or not isinstance(commit.get("confirmed", False), bool):
        raise ValueError("commit requested and confirmed must be boolean")
    if commit.get("confirmed") and not commit.get("requested"):
        raise ValueError("commit.confirmed requires commit.requested")
    if commit.get("requested") and (not isinstance(commit.get("message"), str) or not commit["message"].strip()):
        raise ValueError("commit.message is required when commit is requested")

    raw_tests = payload.get("test_paths")
    if not isinstance(raw_tests, list) or not raw_tests:
        raise ValueError("test_paths must contain at least one test")
    test_paths = [_clean_project_path(path, "test_paths") for path in raw_tests]
    if any(not path.startswith("tests/") for path in test_paths):
        raise ValueError("test_paths must stay under tests/")

    raw_groups = payload.get("stage_groups")
    if not isinstance(raw_groups, dict):
        raise ValueError("stage_groups must be an object")
    unknown_groups = set(raw_groups) - set(_STAGE_GROUP_NAMES)
    if unknown_groups:
        raise ValueError(f"unknown stage groups: {sorted(unknown_groups)}")

    stage_groups: dict[str, list[str]] = {}
    all_paths: list[str] = []
    for group_name in _STAGE_GROUP_NAMES:
        raw_paths = raw_groups.get(group_name, [])
        if not isinstance(raw_paths, list):
            raise ValueError(f"stage_groups.{group_name} must be a list")
        paths = [_clean_project_path(path, f"stage_groups.{group_name}") for path in raw_paths]
        stage_groups[group_name] = paths
        all_paths.extend(paths)
    if not stage_groups["source"]:
        raise ValueError("stage_groups.source must contain at least one source file")
    if len(all_paths) != len(set(all_paths)):
        raise ValueError("a path may belong to only one stage group")

    activation = payload.get("activation")
    if not isinstance(activation, dict) or not isinstance(activation.get("required"), bool):
        raise ValueError("activation.required must be boolean")
    for key in ("target", "method", "verification"):
        if not isinstance(activation.get(key), str):
            raise ValueError(f"activation.{key} must be text")
    if activation["required"] and (not activation["target"].strip() or not activation["method"].strip()):
        raise ValueError("required activation needs target and method")

    return {
        "request": payload,
        "change_set_id": change_set_id,
        "dry_run": bool(dry_run),
        "patch_text": patch_text,
        "test_paths": test_paths,
        "stage_groups": stage_groups,
        "writes": writes,
        "source_write_confirmed": source_write_confirmed,
        "write_backups": {},
        "commit": commit,
        "activation": activation,
    }


@tool("sps_source_patch_check")
def _patch_check_tool(patch_text: str) -> dict:
    """Git unified diff를 적용하지 않고 검사한다."""
    return source_patch(patch_text, dry_run=True)


@tool("sps_source_patch_apply")
def _patch_apply_tool(patch_text: str) -> dict:
    """검사된 Git unified diff를 프로젝트 파일에 적용한다."""
    return source_patch(patch_text, dry_run=False)


@tool("sps_source_write_approved")
def _source_write_tool(
    path: str, content: str, overwrite: bool, create_parent: bool
) -> dict:
    """명시적으로 승인된 source_write 한 건을 원자적으로 실행한다."""
    return source_write(
        path=path,
        content=content,
        overwrite=overwrite,
        create_parent=create_parent,
    )


@tool("sps_pytest_verify")
def _pytest_tool(test_paths: list[str], title: str) -> dict:
    """지정된 회귀 테스트를 실행하고 구조화 결과를 반환한다."""
    return run_pytest_verification(test_paths, title=title)


@tool("sps_git_add_exact")
def _git_add_tool(paths: list[str], dry_run: bool) -> dict:
    """명시된 파일만 Git 인덱스에 올리거나 사전 검사한다."""
    return git_add(paths, dry_run=dry_run)


@tool("sps_git_commit_approved")
def _git_commit_tool(message: str, expected_paths: list[str], dry_run: bool) -> dict:
    """명시적으로 승인된 경우에만 정확한 staged 경로를 commit한다."""
    return git_commit(message=message, expected_paths=expected_paths, dry_run=dry_run)


def _staged_paths() -> list[str]:
    """기존 staged 파일을 읽어 사용자의 다른 작업과 섞이지 않게 한다."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _reverse_patch(patch_text: str) -> None:
    """테스트 실패 시 방금 적용한 패치만 역적용해 원본을 복구한다."""
    command = ["git", "apply", "--reverse", "--recount", "--whitespace=error-all", "-"]
    check = subprocess.run(
        [*command[:-1], "--check", "-"],
        cwd=PROJECT_ROOT,
        input=patch_text,
        text=True,
        capture_output=True,
    )
    if check.returncode != 0:
        raise RuntimeError(f"reverse patch check failed: {check.stderr.strip()}")
    applied = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        input=patch_text,
        text=True,
        capture_output=True,
    )
    if applied.returncode != 0:
        raise RuntimeError(f"reverse patch failed: {applied.stderr.strip()}")


def _unstage_paths(paths: list[str]) -> None:
    """단계 저장 중 오류가 나면 이번 변경 세트의 경로만 인덱스에서 내린다."""
    if not paths:
        return
    subprocess.run(
        ["git", "restore", "--staged", "--", *paths],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )


def _write_change_set_evidence(change_set_id: str, result: dict[str, Any]) -> str:
    """패치 본문을 제외한 실행 증빙을 원자적으로 보존한다."""
    report = PROJECT_ROOT / "harness/memory/orchestrator_runs" / f"change-set-{change_set_id}.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    temporary = report.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, report)
    return str(report.relative_to(PROJECT_ROOT))


def _validate_node(state: ChangeSetState) -> ChangeSetState:
    return _validate_request(state["request"], state["dry_run"])


def _patch_check_node(state: ChangeSetState) -> ChangeSetState:
    if state["patch_text"].strip():
        patch_plan = _patch_check_tool.invoke({"patch_text": state["patch_text"]})
    else:
        patch_plan = {"dry_run": True, "applicable": True, "paths": []}
    expected = {path for paths in state["stage_groups"].values() for path in paths}
    write_paths = {value["path"] for value in state["writes"]}
    actual = set(patch_plan.get("paths", [])) | write_paths
    if actual != expected:
        raise ValueError(
            f"change paths and stage_groups differ: changes={sorted(actual)}, stage={sorted(expected)}"
        )
    return {"patch_plan": patch_plan}


def _after_patch_check(state: ChangeSetState) -> str:
    return "stage_plan" if state["dry_run"] else "apply_patch"


def _stage_plan_node(state: ChangeSetState) -> ChangeSetState:
    write_paths = {value["path"] for value in state["writes"]}
    for paths in state["stage_groups"].values():
        existing_paths = [path for path in paths if path not in write_paths]
        if existing_paths:
            _git_add_tool.invoke({"paths": existing_paths, "dry_run": True})
    commit_state = (
        "AWAITING_APPROVAL" if state["commit"].get("requested") else "NOT_REQUESTED"
    )
    return {
        "state": "PLANNED",
        "success": True,
        "staged_groups": state["stage_groups"],
        "commit_state": commit_state,
    }


def _restore_writes(backups: dict[str, dict[str, Any]]) -> None:
    """테스트나 staging 실패 시 승인된 write 이전의 파일 상태를 복구한다."""
    for path, backup in reversed(list(backups.items())):
        target = (PROJECT_ROOT / path).resolve()
        if backup["existed"]:
            source_write(
                path=path,
                content=backup["content"],
                overwrite=True,
                create_parent=True,
            )
        else:
            target.unlink(missing_ok=True)


def _apply_patch_node(state: ChangeSetState) -> ChangeSetState:
    existing = _staged_paths()
    if existing:
        raise ValueError(f"pre-existing staged files must be cleared first: {existing}")
    patch_applied = False
    backups: dict[str, dict[str, Any]] = {}
    write_results: list[dict[str, Any]] = []
    try:
        if state["patch_text"].strip():
            _patch_apply_tool.invoke({"patch_text": state["patch_text"]})
            patch_applied = True
        for request in state["writes"]:
            target = (PROJECT_ROOT / request["path"]).resolve()
            existed = target.exists()
            backups[request["path"]] = {
                "existed": existed,
                "content": target.read_text(encoding="utf-8") if existed else "",
            }
            write_results.append(_source_write_tool.invoke(request))
    except Exception:
        _restore_writes(backups)
        if patch_applied:
            _reverse_patch(state["patch_text"])
        raise
    return {"write_backups": backups, "write_results": write_results}


def _test_node(state: ChangeSetState) -> ChangeSetState:
    result = _pytest_tool.invoke(
        {
            "test_paths": state["test_paths"],
            "title": f"SPS change set {state['change_set_id']}",
        }
    )
    return {"test_result": result}


def _after_test(state: ChangeSetState) -> str:
    return "stage_apply" if state["test_result"].get("success") else "rollback"


def _stage_apply_node(state: ChangeSetState) -> ChangeSetState:
    touched: list[str] = []
    try:
        for group_name in _STAGE_GROUP_NAMES:
            paths = state["stage_groups"][group_name]
            if not paths:
                continue
            _git_add_tool.invoke({"paths": paths, "dry_run": True})
            _git_add_tool.invoke({"paths": paths, "dry_run": False})
            touched.extend(paths)
    except Exception:
        _unstage_paths(touched)
        _restore_writes(state.get("write_backups", {}))
        if state["patch_text"].strip():
            _reverse_patch(state["patch_text"])
        raise
    commit_state = (
        "AWAITING_APPROVAL" if state["commit"].get("requested") else "NOT_REQUESTED"
    )
    return {
        "state": "STAGED",
        "success": True,
        "staged_groups": state["stage_groups"],
        "commit_state": commit_state,
    }


def _after_stage_apply(state: ChangeSetState) -> str:
    commit = state["commit"]
    return "commit" if commit.get("requested") and commit.get("confirmed") else "evidence"


def _commit_node(state: ChangeSetState) -> ChangeSetState:
    expected_paths = sorted(path for paths in state["stage_groups"].values() for path in paths)
    arguments = {"message": state["commit"]["message"], "expected_paths": expected_paths}
    _git_commit_tool.invoke({**arguments, "dry_run": True})
    result = _git_commit_tool.invoke({**arguments, "dry_run": False})
    return {
        "state": "COMMITTED",
        "success": True,
        "commit_state": "COMMITTED",
        "commit_result": result,
    }


def _rollback_node(state: ChangeSetState) -> ChangeSetState:
    _restore_writes(state.get("write_backups", {}))
    if state["patch_text"].strip():
        _reverse_patch(state["patch_text"])
    return {"state": "ROLLED_BACK", "success": False, "staged_groups": {}, "commit_state": "NOT_RUN"}


def _evidence_node(state: ChangeSetState) -> ChangeSetState:
    evidence = {
        "change_set_id": state["change_set_id"],
        "state": state["state"],
        "success": state["success"],
        "patch_plan": state["patch_plan"],
        "write_results": state.get("write_results", []),
        "test_result": state.get("test_result"),
        "staged_groups": state.get("staged_groups", {}),
        "commit_state": state.get("commit_state", "NOT_RUN"),
        "commit_result": state.get("commit_result"),
        "activation": state["activation"],
    }
    path = _write_change_set_evidence(state["change_set_id"], evidence)
    return {"evidence_path": path}


def _after_stage_plan(state: ChangeSetState) -> str:
    return END if state["dry_run"] else "evidence"


def _build_change_set_graph():
    """결정적 순서와 실패 롤백을 가진 SPS 변경 세트 그래프를 만든다."""
    builder = StateGraph(ChangeSetState)
    builder.add_node("validate", _validate_node)
    builder.add_node("patch_check", _patch_check_node)
    builder.add_node("stage_plan", _stage_plan_node)
    builder.add_node("apply_patch", _apply_patch_node)
    builder.add_node("test", _test_node)
    builder.add_node("stage_apply", _stage_apply_node)
    builder.add_node("commit", _commit_node)
    builder.add_node("rollback", _rollback_node)
    builder.add_node("evidence", _evidence_node)
    builder.add_edge(START, "validate")
    builder.add_edge("validate", "patch_check")
    builder.add_conditional_edges(
        "patch_check",
        _after_patch_check,
        {"stage_plan": "stage_plan", "apply_patch": "apply_patch"},
    )
    builder.add_edge("stage_plan", END)
    builder.add_edge("apply_patch", "test")
    builder.add_conditional_edges(
        "test",
        _after_test,
        {"stage_apply": "stage_apply", "rollback": "rollback"},
    )
    builder.add_conditional_edges(
        "stage_apply",
        _after_stage_apply,
        {"commit": "commit", "evidence": "evidence"},
    )
    builder.add_edge("commit", "evidence")
    builder.add_edge("rollback", "evidence")
    builder.add_edge("evidence", END)
    return builder.compile()


CHANGE_SET_GRAPH = _build_change_set_graph()


def run_change_set(payload: dict[str, Any], dry_run: bool = True) -> dict[str, Any]:
    """LangGraph로 변경 세트를 계획하거나 승인된 실행을 끝까지 수행한다."""
    initial: ChangeSetState = {"request": payload, "dry_run": bool(dry_run)}
    result = CHANGE_SET_GRAPH.invoke(initial)
    result.pop("request", None)
    result.pop("patch_text", None)
    result.pop("writes", None)
    result.pop("write_backups", None)
    return dict(result)
