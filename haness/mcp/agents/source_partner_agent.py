"""LLM이 저장소를 조사하고 검증된 변경 세트를 실행하는 PARTNER 에이전트."""
from __future__ import annotations

import json
import os
import re
from functools import wraps
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

import config as project_config
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from common.auth import CommonAuth
# 2026-11-01: PARTNER Ollama 주소 자동 선택(GPU 서버 → 노트북 터널 → 개발 서버 CPU)
from common.common_function import resolve_ollama_base_url
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
5. 파일 일부만 stage할 때는 stage_patch_groups에 현재 worktree 변경의 정확한 patch만 넣는다.
6. 도구 결과에 없는 성공을 주장하지 말고, 승인 대기나 실패를 그대로 한국어로 보고한다.

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

안전 절차(위 작업 순서를 구체화하며, staging 시점은 이 규칙을 우선 적용):
1. get_git_status 후 source_search/source_read로 대상·호출부·테스트와 기존 staged/worktree 변경을 확인한다. 변경을 분리할 수 없으면 쓰기 전에 멈춘다.
2. 잘못된 입력·재현 테스트를 먼저 설계하고 최소 patch를 준비한다. 기존 파일은 source_patch dry-run, 신규 파일은 change_set의 writes 계획을 검토한다.
3. dry-run의 적용 가능성·SHA-256·patch를 확인한 뒤 같은 변경만 적용한다. 해시 불일치·충돌·승인 누락이면 중단한다.
4. 적용 후 재조회하고 대상별 get_git_diff로 의도한 변경만 있는지 확인한다.
5. 집중 테스트와 전체 회귀를 순서대로 실행한다. 이 단계 전 change_set의 stage_groups는 모두 빈 배열로 두며, 실패·미실행은 통과로 표시하지 않는다.
6. 두 테스트가 통과한 뒤 정확한 경로만 git_add한다. 기존 staged/worktree 변경을 보존하고 별도 요청 없이는 커밋하지 않는다.
7. 실행 중 서비스가 해당 소스를 읽는다는 근거가 있을 때만 RELOAD를 판정한다. 단계별 명령·해시·diff·테스트·staging·미확인 항목을 보고한다.
""".strip()

_ALLOWED_SOURCE_SUFFIXES = {
    ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".txt", ".js", ".ts", ".tsx", ".jsx", ".sql", ".sh", ".ps1",
}
_SEARCH_IGNORED_PARTS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
}
_CHROMIUM_ALLOWED_PREFIXES = ("haness/apps/", "FastAPI/LangGraph/")


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


# 수리 범위 사전 차단(2026-10-25 LuckyBoys: 사후 원복이 아니라 적용 전에 막는다 — 원본 보존 지침 7).
_PATCH_FILE_LINE = re.compile(r"^(?:---|\+\+\+) (?:[ab]/)?(\S+)", re.MULTILINE)
_NEW_TEST_PREFIX = "haness/tests/"


def _enforce_change_scope(payload: dict[str, Any], allowed_source_paths: Sequence[str]) -> None:
    """변경 세트가 허용 범위 안인지 run_change_set 전에 검사하고, 아니면 ValueError로 거부한다.

    - patch_text: 허용 소스(allowed_source_paths)만 수정 가능
    - writes   : haness/tests/ 아래 '아직 없는 새 파일'만 추가 가능(overwrite 금지 → 기존 테스트 수정 불가)
    - stage_groups: 허용 소스 + 이번에 새로 만든 테스트만 stage 가능
    거부는 ToolMessage 오류로 모델에 돌아가므로(handle_tool_errors) 모델이 범위 안에서 다시 시도한다.
    """
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
    staged = {str(p).strip().replace("\\", "/") for paths in (groups.values() if isinstance(groups, dict) else [])
              for p in (paths or [])}
    outside_stage = sorted(staged - allowed - new_tests)
    if outside_stage:
        raise ValueError(f"change scope: stage_groups outside allowed scope: {outside_stage}")


_MCP_WRITE_TOOLS = {
    "source_patch", "source_write", "source_delete", "source_rename",
    "git_add", "git_stage_delete", "git_commit",
    # The local change-set graph mutates files/index; require diff proof before success.
    "execute_change_set",
    "verified_sql_register", "verified_sql_execute",
    "mongodb_save_document", "mongodb_update_document",
}


async def _load_sps_mcp_tools(*, source_write_confirmed: bool) -> list[BaseTool]:
    """SPS MCP tools/list를 호출하고 승인된 범위의 도구만 PARTNER에 노출한다.

    워커는 부모 프로세스의 MCP 세션을 상속하지 않으므로 endpoint와 CommonAuth
    access token으로 독립 Streamable HTTP 세션을 만든다. 토큰 원문은 결과에
    남기지 않으며, 쓰기 도구는 호출 경계 승인값이 없으면 차단한다.
    """
    url = os.getenv("SPS_MCP_URL", "http://127.0.0.1:8000/mcp").strip()
    token = os.getenv("SPS_MCP_BEARER_TOKEN", "").strip()
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
    if source_write_confirmed:
        return tools
    return [mcp_tool for mcp_tool in tools if mcp_tool.name not in _MCP_WRITE_TOOLS]


def build_partner_tools(
    *,
    dry_run: bool,
    source_write_confirmed: bool,
    commit_confirmed: bool,
    allowed_source_paths: Sequence[str] | None = None,
) -> list[BaseTool]:
    """호출자가 확정한 실행·승인 값을 폐쇄 변수로 고정한 PARTNER 도구를 만든다.

    allowed_source_paths(2026-10-25 추가): None이면 기존 동작 그대로(범위 제한 없음).
    값이 있으면 execute_change_set이 적용 전에 _enforce_change_scope로 범위를 검사한다.
    """

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

    @tool("run_chromium_check")
    async def run_chromium_check(
        path: str,
        dry_run: bool = True,
        execute_confirmed: bool = False,
    ) -> str:
        """허용된 로컬 HTML만 Chromium으로 열어 실행 계획 또는 결과를 반환한다.

        dry_run=True 또는 execute_confirmed=False이면 브라우저를 실행하지 않는다.
        경로·브라우저 종류·실행 시점은 이 도구 안에서 고정해 임의 셸 실행을 차단한다.
        """
        # 2026-10-31 회귀 수정: 공통 소스 허용 확장자에는 .html이 없어 Chromium 검사가
        # "path suffix is not allowed"로 먼저 실패했다. 이 도구에서만 .html을 추가로 허용하고,
        # 아래 .html·허용 루트 검사는 그대로 유지해 다른 읽기 도구의 범위는 넓히지 않는다.
        normalized, resolved = _safe_project_file(path, allowed_suffixes=_ALLOWED_SOURCE_SUFFIXES | {".html"})
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
            try:
                page = await browser.new_page()
                await page.goto(resolved.as_uri(), wait_until="load")
                plan.update({"status": "executed", "title": await page.title(), "url": page.url})
            finally:
                await browser.close()
        return _json_result(plan)

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
        # 2026-11-01 LuckyBoys 선택 ①: 주소를 직접 지정하지 않았으면 후보 중 처음 응답하는 Ollama를 쓴다.
        # 후보가 모두 꺼져 있으면 RuntimeError(시도 내역 포함)로 바로 알린다(모델 대기 300초를 낭비하지 않음).
        selected = resolve_ollama_base_url(
            project_config.SPS_SOURCE_PARTNER_OLLAMA_BASE_URL,
            project_config.SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES,
            project_config.SPS_SOURCE_PARTNER_OLLAMA_PROBE_TIMEOUT_SECONDS,
        )
        return ChatOllama(
            model=project_config.SPS_SOURCE_PARTNER_OLLAMA_MODEL,
            base_url=selected["base_url"],
            temperature=0,
            client_kwargs={
                "timeout": project_config.SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS,
            },
        )
    raise ValueError(
        "model provider must be 'gemini' or 'ollama' (SPS_SOURCE_PARTNER_MODEL_PROVIDER)")


def build_source_partner_graph(*, model: Any, tools: Sequence[BaseTool], system_prompt: str | None = None):
    """LangChain 모델과 ToolNode가 실제로 왕복하는 PARTNER LangGraph를 컴파일한다.

    system_prompt(2026-10-25 추가): None이면 기존 _PARTNER_SYSTEM_PROMPT. 페르소나 체인은
    haness/personas/references/<페르소나>.md 원문을 그대로 넣는다(LuckyBoys: 프롬프트 원문 그대로).
    """
    prompt = _PARTNER_SYSTEM_PROMPT if system_prompt is None else system_prompt
    bound_model = model.bind_tools(list(tools))

    async def partner_node(state: MessagesState) -> dict[str, Any]:
        # 시스템 역할을 매 호출에 고정해 도구 결과 뒤의 후속 판단에도 정책이 유지되게 한다.
        response = await bound_model.ainvoke([
            SystemMessage(content=prompt),
            *state["messages"],
        ])
        return {"messages": [response]}

    def route_after_partner(state: MessagesState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(MessagesState)
    graph.add_node("partner", partner_node)
    # 2026-10-25: 도구 예외(예: 허용되지 않은 파일 읽기)를 ToolMessage 오류로 모델에 돌려준다.
    # 예전에는 예외 하나로 그래프 전체가 죽었다(autonomous repair attempt4 실측). 모델이 다른 길을 찾게 한다.
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
    """사용자 작업을 실제 LLM 도구 루프로 수행하고 도구 증빙과 최종 답변을 반환한다.

    recursion_limit(2026-10-25 추가): 조사+재현+수리처럼 도구 왕복이 많은 작업은 호출자가 늘린다.
    기본 18은 기존 동작 그대로다.
    """
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be non-empty text")
    normalized_task = task.strip()
    if len(normalized_task) > 12000:
        raise ValueError("task exceeds 12000 characters")

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
    final_content = messages[-1].content if messages else ""
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
    return {
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


# The existing file can contain unrelated uncommitted work, so keep this
# compatibility layer appended and leave earlier definitions byte-for-byte intact.
from contextvars import ContextVar as _ContextVar
from common.common_function import resolve_project_source_file as _resolve_project_source_file

_mcp_tools_bridge_error: _ContextVar[str | None] = _ContextVar(
    "sps_mcp_tools_bridge_error", default=None)
_mcp_tools_force_read_only: _ContextVar[bool] = _ContextVar(
    "sps_mcp_tools_force_read_only", default=False)


def _safe_project_file(path: str, allowed_suffixes: Any = None) -> tuple[str, Path]:
    """PARTNER source reads share the common traversal, symlink, and suffix guard."""
    return _resolve_project_source_file(
        PROJECT_ROOT, path,
        # allowed_suffixes를 생략하면 기존과 같이 _ALLOWED_SOURCE_SUFFIXES만 허용한다(기존 호출부 동작 불변).
        # run_chromium_check처럼 특정 도구가 확장자를 더 허용해야 할 때만 호출부에서 명시적으로 넘긴다.
        allowed_suffixes=_ALLOWED_SOURCE_SUFFIXES if allowed_suffixes is None else allowed_suffixes)


_original_mcp_tools_loader = _load_sps_mcp_tools


async def _load_sps_mcp_tools(*, source_write_confirmed: bool) -> list[BaseTool]:
    """Gateway failures fall back to local tools; scoped jobs never expose MCP writers."""
    try:
        return await _original_mcp_tools_loader(
            source_write_confirmed=bool(source_write_confirmed and not _mcp_tools_force_read_only.get()))
    except Exception as error:
        _mcp_tools_bridge_error.set(type(error).__name__)
        return []


_original_run_source_partner_agent = run_source_partner_agent


@wraps(_original_run_source_partner_agent)
async def run_source_partner_agent(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Retain the live LLM/ToolNode loop when the nested MCP gateway rejects auth."""
    error_token = _mcp_tools_bridge_error.set(None)
    read_only_token = _mcp_tools_force_read_only.set(
        kwargs.get("allowed_source_paths") is not None)
    try:
        result = await _original_run_source_partner_agent(*args, **kwargs)
        bridge_error = _mcp_tools_bridge_error.get()
    finally:
        _mcp_tools_force_read_only.reset(read_only_token)
        _mcp_tools_bridge_error.reset(error_token)
    if bridge_error:
        result["mcp_tools_bridge_error"] = bridge_error
    return result


# Defend the scoped write boundary even if a custom MCP adapter ignores its
# source_write_confirmed=False argument and returns a write tool anyway.
_scoped_mcp_tools_loader = _load_sps_mcp_tools


async def _load_sps_mcp_tools(*, source_write_confirmed: bool) -> list[BaseTool]:
    loaded = await _scoped_mcp_tools_loader(source_write_confirmed=source_write_confirmed)
    if _mcp_tools_force_read_only.get():
        return [item for item in loaded if getattr(item, "name", None) not in _MCP_WRITE_TOOLS]
    return loaded
