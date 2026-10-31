"""SPS Repository First 소스 분석·변경 검증 흐름을 LangGraph로 고정한다.

분석 순서:
1) source_search -> source_read
2) source_patch dry-run
3) 승인된 경우 source_patch apply
4) git_diff 재확인
5) change_set 내부 pytest/staging/rollback
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from harness.mcp.tools.git_tools import git_diff
from harness.mcp.tools.source_tools import source_read, source_search
from haness.mcp.tools.change_set_graph import run_change_set


class SourceAnalysisState(TypedDict, total=False):
    request: dict[str, Any]
    dry_run: bool
    search_results: list[dict[str, Any]]
    source_reads: list[dict[str, Any]]
    change_set: dict[str, Any]
    git_diff: dict[str, Any]
    state: str
    success: bool


def _validate(state: SourceAnalysisState) -> SourceAnalysisState:
    request = state.get("request")
    if not isinstance(request, dict) or request.get("mode") != "source_analysis":
        raise ValueError("mode must be source_analysis")
    keyword = request.get("keyword")
    if not isinstance(keyword, str) or not keyword.strip():
        raise ValueError("keyword must be non-empty text")
    targets = request.get("read_targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("read_targets must contain at least one item")
    for index, target in enumerate(targets):
        if not isinstance(target, dict) or not isinstance(target.get("path"), str):
            raise ValueError(f"read_targets[{index}].path is required")
        if not isinstance(target.get("start_line", 1), int) or not isinstance(target.get("max_lines", 200), int):
            raise ValueError(f"read_targets[{index}] line bounds must be integers")
    change_set = request.get("change_set")
    if not isinstance(change_set, dict):
        raise ValueError("change_set must be an object")
    return {"request": request}


def _search(state: SourceAnalysisState) -> SourceAnalysisState:
    request = state["request"]
    results = source_search(
        keyword=request["keyword"],
        max_results=int(request.get("max_results", 20)),
        case_sensitive=bool(request.get("case_sensitive", False)),
    )
    return {"search_results": results}


def _read(state: SourceAnalysisState) -> SourceAnalysisState:
    reads = []
    for target in state["request"]["read_targets"]:
        reads.append(source_read(
            path=target["path"],
            start_line=target.get("start_line", 1),
            max_lines=target.get("max_lines", 200),
        ))
    return {"source_reads": reads}


def _change_set(state: SourceAnalysisState) -> SourceAnalysisState:
    result = run_change_set(state["request"]["change_set"], dry_run=state["dry_run"])
    return {"change_set": result}


def _diff(state: SourceAnalysisState) -> SourceAnalysisState:
    result = git_diff(
        path=state["request"].get("diff_path"),
        staged=bool(state["request"].get("diff_staged", False)),
        max_lines=int(state["request"].get("diff_max_lines", 500)),
    )
    return {"git_diff": result, "state": "VERIFIED", "success": bool(state["change_set"].get("success", False))}


def _build_graph():
    graph = StateGraph(SourceAnalysisState)
    graph.add_node("validate", _validate)
    graph.add_node("source_search", _search)
    graph.add_node("source_read", _read)
    graph.add_node("change_set", _change_set)
    graph.add_node("git_diff", _diff)
    graph.add_edge(START, "validate")
    graph.add_edge("validate", "source_search")
    graph.add_edge("source_search", "source_read")
    graph.add_edge("source_read", "change_set")
    graph.add_edge("change_set", "git_diff")
    graph.add_edge("git_diff", END)
    return graph.compile()


SOURCE_ANALYSIS_GRAPH = _build_graph()


def run_source_analysis(payload: dict[str, Any], dry_run: bool = True) -> dict[str, Any]:
    """검색·읽기 후 기존 변경 세트 게이트를 실행하고 증거를 반환한다."""
    result = SOURCE_ANALYSIS_GRAPH.invoke({"request": payload, "dry_run": bool(dry_run)})
    return dict(result)
