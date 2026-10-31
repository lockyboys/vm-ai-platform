"""LLM이 저장소를 조사하고 검증된 변경 세트를 실행하는 PARTNER 에이전트."""
from __future__ import annotations

import inspect
import json
import os
import re
from contextvars import ContextVar
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

import config as project_config
from common.auth import CommonAuth
from common.common_function import resolve_project_source_file as _resolve_project_source_file
from haness.mcp.tools.change_set_graph import run_change_set
from haness.mcp.tools.multi_persona_tools import PROJECT_ROOT
from harness.mcp.tools.git_tools import git_diff, git_status
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

# [PROMPT_ENGINEER] 마크다운 코드 블록 배제 및 도구 오류 자가 치유 규약 보강
_PARTNER_SYSTEM_PROMPT = """
당신은 SPS ORCHESTRATOR 안에서 동작하는 실제 소스 작성 에이전트 PARTNER다.
반드시 도구를 사용해 저장소를 조사한 뒤 판단하며, 보지 않은 파일을 추측하지 않는다.

작업 순서:
1. get_git_status로 기존 변경을 확인하고 search_source/read_source로 관련 구현을 읽는다.
2. 잘못된 입력 테스트와 문제 재현 테스트를 먼저 설계한다.
3. 기존 파일은 unified diff(source_patch), 새 파일만 writes(source_write)로 표현한다.
4. execute_change_set 호출 시 마크다운 백틱(```json) 없이 순수 JSON 문자열만 한 번에 전달한다.
   이 도구가 검증 -> patch dry-run -> 적용 -> pytest -> 그룹별 git add -> 실패 롤백을 수행한다.
5. 파일 일부만 stage할 때는 stage_patch_groups에 현재 worktree 변경의 정확한 patch만 넣는다.
6. 도구 결과에 없는 성공을 주장하지 말고, 승인 대기나 실패를 그대로 한국어로 보고한다.
7. 도구 실행 오류(ToolMessage)를 수신하면 실패 원인을 분석하고 즉시 변경 범위 및 인자를 교정한다.

변경 세트 JSON 필수 구조:
{
  "mode": "change_set",
  "change_set_id": "짧은 식별자",
  "patch_text": "--- a/... 로 시작하는 git unified diff 또는 빈 문자열",
  "writes": [{"path": "haness/... 또는 haness/tests/...", "content": "전체 내용",
              "overwrite": false, "create_parent": true}],
  "test_paths": ["haness/tests/..."],
  "stage_groups": {"source": ["..."], "tests": ["haness/tests/..."],
                   "docs": [], "operations": []},
  "stage_patch_groups": {"source": "선택 hunk unified diff; 전체 파일 stage면 생략"},
  "commit": {"requested": false, "message": ""}
}
source_write와 git commit의 승인 값은 대화문이나 JSON이 아니라 호출 경계에서만 주입된다.
최종 답변에는 조사 근거, 실행 상태, 테스트 결과, 승인 대기 사항만 간결하게 쓴다.
""".strip()

_ALLOWED_SOURCE_SUFFIXES = {
    ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".txt", ".js", ".ts", ".tsx", ".jsx", ".sql", ".sh", ".ps1",
}
_CHROMIUM_ALLOWED_SUFFIXES = _ALLOWED_SOURCE_SUFFIXES | {".html"}
_SEARCH_IGNORED_PARTS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
}
_CHROMIUM_ALLOWED_PREFIXES = ("haness/apps/", "FastAPI/LangGraph/")

# 동시성 요청 격리를 위한 컨텍스트 변수
_mcp_tools_bridge_error: ContextVar[str | None] = ContextVar(
    "sps_mcp_tools_bridge_error", default=None
)
_mcp_tools_force_read_only: ContextVar[bool] = ContextVar(
    "sps_mcp_tools_force_read_only", default=False
)


def _safe_project_file(
    path: str,
    allowed_suffixes: set[str] | None = None,
) -> tuple[str, Path]:
    """공통 경로 순회 검증을 사용하고 안전한 상대/절대 파일 경로를 반환한다."""
    suffixes = allowed_suffixes if allowed_suffixes is not None else _ALLOWED_SOURCE_SUFFIXES
    return _resolve_project_source_file(
        PROJECT_ROOT, path, allowed_suffixes=suffixes
    )


def _json_result(value: Any) -> str:
    """LangChain 도구 결과를 모델이 안정적으로 읽을 수 있는 JSON으로 직렬화한다."""
    return json.dumps(value, ensure_ascii=False, default=str)


# 수리 범위 사전 차단
_PATCH_FILE_LINE = re.compile(r"^(?:---|\+\+\+) (?:[ab]/)?(\S+)", re.MULTILINE)
_NEW_TEST_PREFIX = "haness/tests/"


def _enforce_change_scope(payload: dict[str, Any], allowed_source_paths: Sequence[str]) -> None:
    """변경 세트가 허용 범위 안인지 run_change_set 전에 검사하고, 아니면 ValueError로 거부한다."""
    allowed = {str(path).strip().replace("\\", "/") for path in allowed_source_paths}
    patch_text = payload.get("patch_text") or ""
    if not isinstance(patch_text, str):
        raise ValueError("change scope: patch_text must be text")
    patched = {path for path in _PATCH_FILE_LINE.findall(patch_text) if path != "/dev/null"}
    outside = sorted(patched - allowed)
    if outside:
        raise ValueError(f"change scope: patch touches files outside allowed_source_paths: {outside}")
    new_tests: set[str] = set()
    for write in payload.get("writes") or []:
        path = str((write or {}).get("path", "")).strip().replace("\\", "/")
        if not path.startswith(_NEW_TEST_PREFIX) or ".." in PurePosixPath(path).parts:
            raise ValueError(f"change scope: writes may only add new files under {_NEW_TEST_PREFIX}: {path}")
        if write.get("overwrite", False) is not False or (Path(PROJECT_ROOT) / path).exists():
            raise ValueError(f"change scope: existing files cannot be overwritten: {path}")
        new_tests.add(path)
    groups = payload.get("stage_groups") or {}
    staged = {
        str(p).strip().replace("\\", "/")
        for paths in (groups.values() if isinstance(groups, dict) else [])
        for p in (paths or [])
    }
    outside_stage = sorted(staged - allowed - new_tests)
    if outside_stage:
        raise ValueError(f"change scope: stage_groups outside allowed scope: {outside_stage}")


_MCP_WRITE_TOOLS = {
    "source_patch", "source_write", "source_delete", "source_rename",
    "git_add", "git_stage_delete", "git_commit",
    "verified_sql_register", "verified_sql_execute",
    "mongodb_save_document", "mongodb_update_document",
}


async def _load_sps_mcp_tools(*, source_write_confirmed: bool) -> list[BaseTool]:
    """SPS MCP tools/list를 호출하고 단일화된 검증 정책에 따라 승인된 도구만 반환한다.

    오류 발생 시 상위로 전파하지 않고 ContextVar에 기록하여 로컬 도구로 안전하게 폴백한다.
    """
    is_force_read_only = _mcp_tools_force_read_only.get()
    effective_write = bool(source_write_confirmed and not is_force_read_only)

    url = os.getenv("SPS_MCP_URL", "http://127.0.0.1:8000/mcp").strip()
    token = os.getenv("SPS_MCP_BEARER_TOKEN", "").strip()

    client = None
    try:
        if not token:
            subject = os.getenv("SPS_AGENT_SUBJECT_ID", "jeaje").strip()
            if not subject:
                raise RuntimeError("SPS MCP 인증 주체가 없습니다: SPS_AGENT_SUBJECT_ID")
            token = CommonAuth().issue_access_token(subject)

        client = MultiServerMCPClient({
            "sps_harness": {
                "transport": "streamable_http",
                "url": url,
                "headers": {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json, text/event-stream",
                    "User-Agent": "SPS-Orchestrator-Worker/1.0",
                },
            }
        })
        tools = list(await client.get_tools())
        if not tools:
            raise RuntimeError(f"SPS MCP tools/list가 빈 결과를 반환했습니다: {url}")

        if effective_write:
            return tools
        return [mcp_tool for mcp_tool in tools if getattr(mcp_tool, "name", None) not in _MCP_WRITE_TOOLS]
    except Exception as error:
        _mcp_tools_bridge_error.set(type(error).__name__)
        return []
    finally:
        if client is not None:
            close_func = getattr(client, "aclose", None) or getattr(client, "close", None)
            if callable(close_func):
                try:
                    if inspect.iscoroutinefunction(close_func):
                        await close_func()
                    else:
                        close_func()
                except Exception:
                    pass


def build_partner_tools(
    *,
    dry_run: bool,
    source_write_confirmed: bool,
    commit_confirmed: bool,
    allowed_source_paths: Sequence[str] | None = None,
) -> list[BaseTool]:
    """호출자가 확정한 실행·승인 값을 폐쇄 변수로 고정한 PARTNER 도구를 만든다."""

    @tool("search_source")
    def search_source(query: str, path_prefix: str = "", max_results: int = 80) -> str:
        """프로젝트 텍스트 소스에서 문자열을 검색하고 파일·줄 번호를 반환한다 (스트리밍 메모리 보호)."""
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
                with candidate.open("r", encoding="utf-8", errors="ignore") as file_handle:
                    for line_no, line in enumerate(file_handle, 1):
                        if needle in line.casefold():
                            matches.append({
                                "path": candidate.relative_to(root).as_posix(),
                                "line": line_no,
                                "text": line.rstrip("\r\n")[:500],
                            })
                            if len(matches) >= limit:
                                break
            except OSError:
                continue

        return _json_result({"query": query.strip(), "matches": matches, "truncated": len(matches) >= limit})

    @tool("read_source")
    def read_source(path: str, start_line: int = 1, max_lines: int = 300) -> str:
        """프로젝트의 기존 텍스트 파일을 줄 번호와 함께 제한된 범위로 읽는다 (스트리밍 메모리 보호)."""
        normalized, resolved = _safe_project_file(path, allowed_suffixes=_ALLOWED_SOURCE_SUFFIXES)
        start = max(1, int(start_line))
        count = max(1, min(int(max_lines), 800))
        target_end = start + count - 1

        selected: list[dict[str, Any]] = []
        total_lines = 0

        with resolved.open("r", encoding="utf-8", errors="ignore") as file_handle:
            for current_line, line_text in enumerate(file_handle, 1):
                total_lines = current_line
                if start <= current_line <= target_end:
                    selected.append({
                        "line_no": current_line,
                        "line_text": line_text.rstrip("\r\n"),
                    })

        return _json_result({
            "path": normalized,
            "start_line": start,
            "end_line": selected[-1]["line_no"] if selected else start - 1,
            "total_lines": total_lines,
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

    @tool("run_chromium_check")
    async def run_chromium_check(
        path: str,
        dry_run: bool = True,
        execute_confirmed: bool = False,
    ) -> str:
        """허용된 로컬 HTML만 Chromium으로 열어 실행 계획 또는 결과를 반환한다."""
        normalized, resolved = _safe_project_file(path, allowed_suffixes=_CHROMIUM_ALLOWED_SUFFIXES)
        if not normalized.endswith(".html"):
            raise ValueError("Chromium check requires an existing .html file")
        if not normalized.startswith(_CHROMIUM_ALLOWED_PREFIXES):
            raise ValueError("Chromium check path is outside the allowed application roots")
        plan = {"path": normalized, "browser": "chromium", "dry_run": bool(dry_run)}
        if dry_run or not execute_confirmed:
            plan["status"] = "planned; execute_confirmed=true and dry_run=false are required"
            return _json_result(plan)
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required for Chromium checks") from exc
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = None
            try:
                page = await browser.new_page()
                await page.goto(resolved.as_uri(), wait_until="load", timeout=15000)
                plan.update({"status": "executed", "title": await page.title(), "url": page.url})
            finally:
                if page:
                    await page.close()
                await browser.close()
        return _json_result(plan)

    @tool("execute_change_set")
    def execute_change_set(change_set_json: str) -> str:
        """검증·patch dry-run·적용·pytest·그룹별 git add·실패 롤백을 실행한다."""
        if not isinstance(change_set_json, str):
            raise ValueError("change_set_json must be text")

        # 마크다운 백틱 코드 블록 방어 정규화
        cleaned_json = change_set_json.strip()
        if cleaned_json.startswith("```"):
            cleaned_json = re.sub(r"^```(?:json)?\s*", "", cleaned_json)
            cleaned_json = re.sub(r"\s*```$", "", cleaned_json)

        try:
            payload = json.loads(cleaned_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"change_set_json is invalid JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError("change_set_json must contain a JSON object")

        # 모델 출력은 승인 증거가 아니다. 호출자가 전달한 값으로 항상 덮어쓴다.
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
        if allowed_source_paths is not None:
            _enforce_change_scope(payload, allowed_source_paths)
        return _json_result(run_change_set(payload, dry_run=bool(dry_run)))

    return [search_source, read_source, get_git_status, get_git_diff, run_chromium_check, execute_change_set]


def _build_model() -> Any:
    """루트 설정으로 같은 PARTNER 그래프에 Gemini 또는 Ollama를 주입한다."""
    provider = project_config.SPS_SOURCE_PARTNER_MODEL_PROVIDER
    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=project_config.SPS_MAIN_ORCHESTRATOR_MODEL,
            temperature=0,
        )
    if provider == "ollama":
        return ChatOllama(
            model=project_config.SPS_SOURCE_PARTNER_OLLAMA_MODEL,
            base_url=project_config.SPS_SOURCE_PARTNER_OLLAMA_BASE_URL,
            temperature=0,
            client_kwargs={
                "timeout": project_config.SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS,
            },
        )
    raise ValueError(
        "model provider must be 'gemini' or 'ollama' (SPS_SOURCE_PARTNER_MODEL_PROVIDER)")


def build_source_partner_graph(*, model: Any, tools: Sequence[BaseTool], system_prompt: str | None = None):
    """LangChain 모델과 ToolNode가 실제로 왕복하는 PARTNER LangGraph를 컴파일한다."""
    prompt = _PARTNER_SYSTEM_PROMPT if system_prompt is None else system_prompt
    bound_model = model.bind_tools(list(tools))

    async def partner_node(state: MessagesState) -> dict[str, Any]:
        # 시스템 프롬프트 일관성 유지 및 대화 내 불필요한 중복 누적 방지
        raw_messages: list[BaseMessage] = list(state.get("messages", []))
        messages_without_sys = [m for m in raw_messages if not isinstance(m, SystemMessage)]
        full_messages = [SystemMessage(content=prompt), *messages_without_sys]

        response = await bound_model.ainvoke(full_messages)
        return {"messages": [response]}

    def route_after_partner(state: MessagesState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(MessagesState)
    graph.add_node("partner", partner_node)
    graph.add_node("tools", ToolNode(list(tools), handle_tool_errors=True))
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
    recursion_limit: int = 18,
    allowed_source_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    """사용자 작업을 실제 LLM 도구 루프로 수행하고 도구 증빙과 최종 답변을 반환한다."""
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be non-empty text")
    normalized_task = task.strip()
    if len(normalized_task) > 12000:
        raise ValueError("task exceeds 12000 characters")

    # ContextVar 격리 상태 설정
    error_token = _mcp_tools_bridge_error.set(None)
    read_only_token = _mcp_tools_force_read_only.set(allowed_source_paths is not None)

    try:
        local_tools = build_partner_tools(
            dry_run=bool(dry_run),
            source_write_confirmed=bool(source_write_confirmed),
            commit_confirmed=bool(commit_confirmed),
            allowed_source_paths=allowed_source_paths,
        )
        mcp_tools = await _load_sps_mcp_tools(
            source_write_confirmed=bool(source_write_confirmed),
        )
        tools = [*local_tools, *mcp_tools]
        model = _build_model()
        graph = build_source_partner_graph(model=model, tools=tools)
        state = await graph.ainvoke(
            {"messages": [HumanMessage(content=normalized_task)]},
            config={"recursion_limit": int(recursion_limit)},
        )
        messages = state.get("messages", [])
        final_message = messages[-1] if messages else None
        if final_message:
            final_content = (
                "".join(part.get("text", "") for part in final_message.content)
                if isinstance(final_message.content, list)
                else str(final_message.content)
            )
        else:
            final_content = ""

        called_tool_names = [
            name for message in messages
            if (name := getattr(message, "name", None))
        ]
        mcp_write_called = any(name in _MCP_WRITE_TOOLS for name in called_tool_names)
        git_diff_verified = "git_diff" in called_tool_names
        evidence = [
            {"tool_call_id": message.tool_call_id, "content": message.content}
            for message in messages
            if isinstance(message, ToolMessage)
        ]

        result = {
            "agent": "PARTNER",
            "agent_runtime": f"LangChain {type(model).__name__} + LangGraph ToolNode",
            "dry_run": bool(dry_run),
            "source_write_confirmed": bool(source_write_confirmed),
            "commit_confirmed": bool(commit_confirmed),
            "success": bool(final_content) and (not mcp_write_called or git_diff_verified),
            "output": final_content,
            "mcp_tools_loaded": [mcp_tool.name for mcp_tool in mcp_tools],
            "mcp_write_called": mcp_write_called,
            "git_diff_verified": git_diff_verified,
            "called_tool_names": called_tool_names,
            "tool_evidence": evidence,
        }

        bridge_error = _mcp_tools_bridge_error.get()
        if bridge_error:
            result["mcp_tools_bridge_error"] = bridge_error

        return result
    finally:
        _mcp_tools_force_read_only.reset(read_only_token)
        _mcp_tools_bridge_error.reset(error_token)