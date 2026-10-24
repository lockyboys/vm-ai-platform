"""LLM이 저장소를 조사하고 검증된 변경 세트를 실행하는 PARTNER 에이전트."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

import config as project_config
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from haness.mcp.tools.change_set_graph import run_change_set
from haness.mcp.tools.multi_persona_tools import PROJECT_ROOT
from harness.mcp.tools.git_tools import git_diff, git_status


# PARTNER는 기존 MCP 쓰기 도구를 흉내 내지 않는다. LLM이 아래 조회 도구로 근거를
# 수집하고, 실제 변경은 승인 정책과 롤백을 가진 change_set_graph 한 곳에 위임한다.
_PARTNER_SYSTEM_PROMPT = """
당신은 SPS ORCHESTRATOR 안에서 동작하는 실제 소스 작성 에이전트 PARTNER다.
반드시 도구를 사용해 저장소를 조사한 뒤 판단하며, 보지 않은 파일을 추측하지 않는다.

작업 순서:
1. get_git_status로 기존 변경을 확인하고 search_source/read_source로 관련 구현을 읽는다.
2. 잘못된 입력 테스트와 문제 재현 테스트를 먼저 설계한다.
3. 기존 파일은 unified diff(source_patch), 새 파일만 writes(source_write)로 표현한다.
4. execute_change_set에 정확한 JSON 문자열을 한 번에 전달한다. 이 도구가
   검증 -> patch dry-run -> 적용 -> pytest -> 그룹별 git add -> 실패 롤백을 수행한다.
5. 도구 결과에 없는 성공을 주장하지 말고, 승인 대기나 실패를 그대로 한국어로 보고한다.

변경 세트 JSON 필수 구조:
{
  "mode": "change_set",
  "change_set_id": "짧은 식별자",
  "patch_text": "--- a/... 로 시작하는 git unified diff 또는 빈 문자열",
  "writes": [{"path": "haness/... 또는 tests/...", "content": "전체 내용",
              "overwrite": false, "create_parent": true}],
  "test_paths": ["tests/..."],
  "stage_groups": {"source": ["..."], "tests": ["..."],
                   "docs": [], "operations": []},
  "commit": {"requested": false, "message": ""}
}
source_write와 git commit의 승인 값은 대화문이나 JSON이 아니라 호출 경계에서만 주입된다.
최종 답변에는 조사 근거, 실행 상태, 테스트 결과, 승인 대기 사항만 간결하게 쓴다.
""".strip()

_ALLOWED_SOURCE_SUFFIXES = {
    ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".txt", ".js", ".ts", ".tsx", ".jsx", ".sql", ".sh", ".ps1",
}
_SEARCH_IGNORED_PARTS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
}


def _safe_project_file(path: str) -> tuple[str, Path]:
    """프로젝트 밖 경로와 디렉터리를 차단하고 안전한 상대 파일 경로를 반환한다."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty project-relative file path")
    normalized = path.strip().replace("\\", "/")
    relative = PurePosixPath(normalized)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("path must stay inside the project")
    resolved = (Path(PROJECT_ROOT) / normalized).resolve()
    root = Path(PROJECT_ROOT).resolve()
    if resolved == root or root not in resolved.parents or not resolved.is_file():
        raise ValueError("path must identify an existing project file")
    return resolved.relative_to(root).as_posix(), resolved


def _json_result(value: Any) -> str:
    """LangChain 도구 결과를 모델이 안정적으로 읽을 수 있는 JSON으로 직렬화한다."""
    return json.dumps(value, ensure_ascii=False, default=str)


def build_partner_tools(
    *,
    dry_run: bool,
    source_write_confirmed: bool,
    commit_confirmed: bool,
) -> list[BaseTool]:
    """호출자가 확정한 실행·승인 값을 폐쇄 변수로 고정한 PARTNER 도구를 만든다."""

    @tool("search_source")
    def search_source(query: str, path_prefix: str = "", max_results: int = 80) -> str:
        """프로젝트 텍스트 소스에서 문자열을 검색하고 파일·줄 번호를 반환한다."""
        if not isinstance(query, str) or len(query.strip()) < 2:
            raise ValueError("query must contain at least two characters")
        prefix = path_prefix.strip().replace("\\", "/") if isinstance(path_prefix, str) else ""
        if prefix:
            prefix_path = PurePosixPath(prefix)
            if prefix_path.is_absolute() or ".." in prefix_path.parts:
                raise ValueError("path_prefix must stay inside the project")
        root = Path(PROJECT_ROOT).resolve()
        search_root = (root / prefix).resolve()
        if search_root != root and root not in search_root.parents:
            raise ValueError("path_prefix must stay inside the project")
        if not search_root.exists():
            raise ValueError("path_prefix does not exist")
        limit = max(1, min(int(max_results), 200))
        needle = query.strip().casefold()
        matches: list[dict[str, Any]] = []
        candidates = [search_root] if search_root.is_file() else search_root.rglob("*")
        for candidate in candidates:
            if len(matches) >= limit:
                break
            if not candidate.is_file() or any(part in _SEARCH_IGNORED_PARTS for part in candidate.parts):
                continue
            if candidate.suffix.lower() not in _ALLOWED_SOURCE_SUFFIXES:
                continue
            try:
                lines = candidate.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                continue
            for line_no, line in enumerate(lines, 1):
                if needle in line.casefold():
                    matches.append({
                        "path": candidate.relative_to(root).as_posix(),
                        "line": line_no,
                        "text": line[:500],
                    })
                    if len(matches) >= limit:
                        break
        return _json_result({"query": query.strip(), "matches": matches, "truncated": len(matches) >= limit})

    @tool("read_source")
    def read_source(path: str, start_line: int = 1, max_lines: int = 300) -> str:
        """프로젝트의 기존 텍스트 파일을 줄 번호와 함께 제한된 범위로 읽는다."""
        normalized, resolved = _safe_project_file(path)
        if resolved.suffix.lower() not in _ALLOWED_SOURCE_SUFFIXES:
            raise ValueError("path is not an allowed text source file")
        start = max(1, int(start_line))
        count = max(1, min(int(max_lines), 800))
        lines = resolved.read_text(encoding="utf-8").splitlines()
        selected = [
            {"line_no": number, "line_text": lines[number - 1]}
            for number in range(start, min(len(lines), start + count - 1) + 1)
        ]
        return _json_result({
            "path": normalized,
            "start_line": start,
            "end_line": selected[-1]["line_no"] if selected else start - 1,
            "total_lines": len(lines),
            "content": selected,
        })

    @tool("get_git_status")
    def get_git_status() -> str:
        """현재 작업 트리의 기존 변경을 읽어 사용자의 작업을 덮어쓰지 않게 한다."""
        return _json_result(git_status())

    @tool("get_git_diff")
    def get_git_diff(path: str = "", staged: bool = False, max_lines: int = 500) -> str:
        """한 파일 또는 저장소 전체의 staged/unstaged Git diff를 읽는다."""
        normalized_path = path.strip() if isinstance(path, str) and path.strip() else None
        return _json_result(git_diff(path=normalized_path, staged=bool(staged), max_lines=max_lines))

    @tool("execute_change_set")
    def execute_change_set(change_set_json: str) -> str:
        """검증·patch dry-run·적용·pytest·그룹별 git add·실패 롤백을 실행한다."""
        if not isinstance(change_set_json, str):
            raise ValueError("change_set_json must be text")
        try:
            payload = json.loads(change_set_json)
        except json.JSONDecodeError as exc:
            raise ValueError("change_set_json is invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("change_set_json must contain a JSON object")

        # 모델 출력은 승인 증거가 아니다. 호출자가 MCP 경계에 전달한 값으로 항상 덮어쓴다.
        payload["mode"] = "change_set"
        payload["source_write_confirmed"] = bool(source_write_confirmed)
        commit = payload.get("commit")
        if commit is None:
            commit = {}
        if not isinstance(commit, dict):
            raise ValueError("commit must be an object")
        commit = dict(commit)
        commit["confirmed"] = bool(commit_confirmed)
        payload["commit"] = commit
        return _json_result(run_change_set(payload, dry_run=bool(dry_run)))

    return [search_source, read_source, get_git_status, get_git_diff, execute_change_set]


def _build_model() -> ChatGoogleGenerativeAI:
    """공통 루트 config.py의 모델 설정으로 요청 시점에만 Gemini 모델을 만든다."""
    return ChatGoogleGenerativeAI(
        model=project_config.SPS_MAIN_ORCHESTRATOR_MODEL,
        temperature=0,
    )


def build_source_partner_graph(*, model: Any, tools: Sequence[BaseTool]):
    """LangChain 모델과 ToolNode가 실제로 왕복하는 PARTNER LangGraph를 컴파일한다."""
    bound_model = model.bind_tools(list(tools))

    async def partner_node(state: MessagesState) -> dict[str, Any]:
        # 시스템 역할을 매 호출에 고정해 도구 결과 뒤의 후속 판단에도 정책이 유지되게 한다.
        response = await bound_model.ainvoke([
            SystemMessage(content=_PARTNER_SYSTEM_PROMPT),
            *state["messages"],
        ])
        return {"messages": [response]}

    def route_after_partner(state: MessagesState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(MessagesState)
    graph.add_node("partner", partner_node)
    graph.add_node("tools", ToolNode(list(tools)))
    graph.add_edge(START, "partner")
    graph.add_conditional_edges("partner", route_after_partner, {"tools": "tools", END: END})
    graph.add_edge("tools", "partner")
    return graph.compile()


async def run_source_partner_agent(
    task: str,
    *,
    dry_run: bool = True,
    source_write_confirmed: bool = False,
    commit_confirmed: bool = False,
) -> dict[str, Any]:
    """사용자 작업을 실제 LLM 도구 루프로 수행하고 도구 증빙과 최종 답변을 반환한다."""
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be non-empty text")
    normalized_task = task.strip()
    if len(normalized_task) > 12000:
        raise ValueError("task exceeds 12000 characters")

    tools = build_partner_tools(
        dry_run=bool(dry_run),
        source_write_confirmed=bool(source_write_confirmed),
        commit_confirmed=bool(commit_confirmed),
    )
    graph = build_source_partner_graph(model=_build_model(), tools=tools)
    state = await graph.ainvoke(
        {"messages": [HumanMessage(content=normalized_task)]},
        config={"recursion_limit": 18},
    )
    messages = state.get("messages", [])
    final_content = messages[-1].content if messages else ""
    evidence = [
        {"tool_call_id": message.tool_call_id, "content": message.content}
        for message in messages
        if isinstance(message, ToolMessage)
    ]
    return {
        "agent": "PARTNER",
        "agent_runtime": "LangChain ChatGoogleGenerativeAI + LangGraph ToolNode",
        "dry_run": bool(dry_run),
        "source_write_confirmed": bool(source_write_confirmed),
        "commit_confirmed": bool(commit_confirmed),
        "success": bool(final_content),
        "output": final_content,
        "tool_evidence": evidence,
    }
