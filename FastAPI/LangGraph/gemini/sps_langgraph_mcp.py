"""LangGraph로 SPS Harness MCP 도구를 조회하고 이름으로 실행한다."""
# 1. 최초 환경 설정
# cd /data/vm_project
# export SCRIPT='/data/vm_project/FastAPI/LangGraph/gemini/sps_langgraph_mcp.py'
# export SPS_MCP_URL='http://127.0.0.1:8000/mcp'
# export SPS_MCP_HOST_HEADER='subprime-glowworm-mundane.ngrok-free.dev'
# export SPS_AUTH_JWT_EXPIRE_SECONDS=900
# export SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS=86400
# 2. 실행 직전에 토큰 발급
#  export SPS_MCP_BEARER_TOKEN="$(
#    PYTHONPATH=/data/vm_project venv/bin/python -c \
#    'from dotenv import load_dotenv; load_dotenv("/data/vm_project/.env"); from common.auth import CommonAuth; print(CommonAuth().issue_access_token("jeaje"))'
#  )"
# 토큰은 900초 후 만료되므로 재실행할 때 다시 발급합니다.

# 3. 툴 41개 목록 조회
# PYTHONPATH=/data/vm_project venv/bin/python "$SCRIPT"
# 4. 조회 툴 실행
#  PYTHONPATH=/data/vm_project venv/bin/python "$SCRIPT" \
#    --tool git_status \
#    --args '{}'
# 5. 변경 툴 실행
# PYTHONPATH=/data/vm_project venv/bin/python "$SCRIPT" \
#   --tool update_current_checkpoint \
#   --args '{"checkpoint_text":"저장할 내용"}' \
#   --approve
# --approve가 없으면 변경 툴은 LangGraph 검증 단계에서 차단됩니다.

# 토큰 발급	 export SPS_AUTH_JWT_EXPIRE_SECONDS=900 SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS=86400 
#           SPS_MCP_HOST_HEADER=subprime-glowworm-mundane.ngrok-free.dev; export 
#           SPS_MCP_BEARER_TOKEN="$(PYTHONPATH=/data/vm_project /data/vm_project/venv/bin/python -c 
#           'from dotenv import load_dotenv; load_dotenv("/data/vm_project/.env"); from common.auth 
#           import CommonAuth; print(CommonAuth().issue_access_token("jeaje"))')"
# 질의 실행	 PYTHONPATH=/data/vm_project /data/vm_project/venv/bin/python 
#           /data/vm_project/FastAPI/LangGraph/gemini/sps_langgraph_mcp.py --query "파일 
#           /data/vm_project/FastAPI/LangGraph/gemini/sps_langgraph_mcp.py를 읽고 OLLAMA_BASE_URL 설정과 
#           sps-harness.service 상태를 확인해 줘"

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any, TypedDict

import httpx2
from dotenv import load_dotenv
from google import genai
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


load_dotenv()

MCP_URL = os.getenv("SPS_MCP_URL", "http://127.0.0.1:18000/mcp")
MCP_TOKEN = os.getenv("SPS_MCP_BEARER_TOKEN", "")
DEFAULT_MODEL_NAME = os.getenv("OLLAMA_MODEL", "gemma4:e4b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


class AgentState(TypedDict, total=False):
    """LangGraph의 각 작업방이 함께 사용하는 공책이다."""

    tool_name: str
    tool_arguments: dict[str, Any]
    approved: bool
    available_tools: dict[str, dict[str, Any]]
    tool_count: int
    next_step: str
    result: str
    error: str


# 이름에 다음 단어가 들어간 도구는 데이터를 변경할 가능성이 있다.
WRITE_KEYWORDS = {
    "write",
    "patch",
    "delete",
    "rename",
    "save",
    "update",
    "insert",
    "add",
    "commit",
    "execute",
    "reconcile",
    "register",
    "backup_create",
}


def is_write_tool(tool_name: str) -> bool:
    """도구 이름을 보고 사용자 승인이 필요한지 보수적으로 판단한다."""

    lower_name = tool_name.lower()
    return any(keyword in lower_name for keyword in WRITE_KEYWORDS)


def result_to_text(call_result: Any) -> str:
    """MCP 실행 결과를 터미널에서 읽을 수 있는 문자열로 바꾼다."""

    if not hasattr(call_result, "content"):
        return str(call_result)

    lines: list[str] = []
    for content_item in call_result.content:
        if hasattr(content_item, "text"):
            lines.append(content_item.text)
        else:
            lines.append(str(content_item))
    return "\n".join(lines)


def json_schema_to_google_schema(schema: dict[str, Any]) -> genai.types.Schema:
    """MCP JSON 입력 규격을 Gemini 함수 호출 규격으로 바꾼다."""

    type_map = {
        "string": genai.types.Type.STRING,
        "integer": genai.types.Type.INTEGER,
        "number": genai.types.Type.NUMBER,
        "boolean": genai.types.Type.BOOLEAN,
        "array": genai.types.Type.ARRAY,
        "object": genai.types.Type.OBJECT,
    }
    properties: dict[str, genai.types.Schema] = {}

    for key, value in schema.get("properties", {}).items():
        value = dict(value)
        value_type = value.get("type")

        # nullable 필드는 anyOf 안에서 null이 아닌 실제 자료형을 사용한다.
        if not value_type and isinstance(value.get("anyOf"), list):
            candidates = [
                item for item in value["anyOf"] if item.get("type") != "null"
            ]
            if candidates:
                value = candidates[0]
                value_type = value.get("type")

        google_type = type_map.get(value_type, genai.types.Type.STRING)
        child: dict[str, Any] = {
            "type": google_type,
            "description": value.get("description", ""),
        }

        if value_type == "array":
            item_type = value.get("items", {}).get("type", "string")
            child["items"] = genai.types.Schema(
                type=type_map.get(item_type, genai.types.Type.STRING)
            )

        properties[key] = genai.types.Schema(**child)

    return genai.types.Schema(
        type=genai.types.Type.OBJECT,
        properties=properties,
        required=schema.get("required", []),
    )


def build_google_mcp_tools(
    available_tools: dict[str, dict[str, Any]],
    approved: bool,
) -> list[genai.types.Tool]:
    """MCP 도구를 Gemini에 제공하되 미승인 변경 도구는 제외한다."""

    declarations: list[genai.types.FunctionDeclaration] = []
    for name, information in sorted(available_tools.items()):
        if is_write_tool(name) and not approved:
            continue
        declarations.append(
            genai.types.FunctionDeclaration(
                name=name,
                description=information["description"] or f"SPS MCP tool: {name}",
                parameters=json_schema_to_google_schema(information["input_schema"]),
            )
        )

    return [genai.types.Tool(function_declarations=declarations)]


def create_google_client() -> genai.Client:
    """환경변수의 API 키로 Google GenAI 클라이언트를 만든다."""

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    api_key = api_key.strip().replace("\n", "").replace("\r", "")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY 또는 GEMINI_API_KEY가 필요합니다.")
    return genai.Client(api_key=api_key)


async def choose_tool_with_google(
    query: str,
    available_tools: dict[str, dict[str, Any]],
    approved: bool,
) -> tuple[str, dict[str, Any], str, Any]:
    """로컬 Ollama Gemma가 답하거나 사용할 MCP 도구 하나를 선택하게 한다."""

    model = ChatOllama(
        model=DEFAULT_MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        options={"num_ctx": 4096, "num_predict": 256},
    )
    visible_tools = {
        name: information
        for name, information in available_tools.items()
        if approved or not is_write_tool(name)
    }
    catalog = [
        {
            "name": name,
            "description": information["description"],
            "input_schema": information["input_schema"],
        }
        for name, information in sorted(visible_tools.items())
    ]
    prompt = (
        "너는 SPS Harness MCP 로컬 에이전트다.\n"
        "사용자 질문에 답하거나 MCP 도구 하나를 선택한다.\n"
        "도구가 필요하면 JSON만 반환한다: "
        '{"tool_name":"도구명","arguments":{}}\n'
        "직접 답할 수 있으면 JSON만 반환한다: "
        '{"answer":"답변"}\n'
        "등록되지 않은 도구명과 추정한 인자는 사용하지 않는다.\n"
        f"사용자 질문: {query}\n"
        f"사용 가능한 도구: {json.dumps(catalog, ensure_ascii=False)}"
    )
    response = await asyncio.to_thread(model.invoke, prompt)
    raw_text = getattr(response, "content", "")
    if not isinstance(raw_text, str):
        raw_text = str(raw_text)
    raw_text = raw_text.strip()
    fence = chr(96) * 3
    if fence in raw_text:
        raw_text = raw_text.split(fence, 2)[1].removeprefix("json").strip()
    try:
        selected = json.loads(raw_text)
    except json.JSONDecodeError:
        return "", {}, raw_text, response
    if selected.get("answer"):
        return "", {}, str(selected["answer"]), response
    return (
        str(selected.get("tool_name", "")),
        dict(selected.get("arguments") or {}),
        "",
        response,
    )


async def summarize_tool_result_with_google(
    query: str,
    tool_name: str,
    tool_arguments: dict[str, Any],
    tool_result: str,
) -> str:
    """MCP 실행 결과를 로컬 Ollama Gemma가 사용자 질문에 맞게 설명하게 한다."""

    prompt = (
        "사용자 질문에 한국어로 정확히 답하세요. 실행하지 않은 내용은 추정하지 마세요.\n"
        f"질문: {query}\n"
        f"실행한 MCP 도구: {tool_name}\n"
        f"도구 입력: {json.dumps(tool_arguments, ensure_ascii=False)}\n"
        f"도구 결과:\n{tool_result}"
    )
    model = ChatOllama(
        model=DEFAULT_MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        options={"num_ctx": 4096, "num_predict": 256},
    )
    response = await asyncio.to_thread(model.invoke, prompt)
    content = getattr(response, "content", "")
    return content if isinstance(content, str) and content.strip() else tool_result


def build_graph(session: ClientSession):
    """현재 MCP 연결을 사용하는 LangGraph를 만든다."""

    async def load_tools_node(state: AgentState) -> dict[str, Any]:
        """SPS Harness MCP에 등록된 모든 도구를 조회한다."""

        del state  # 이 작업방은 이전 State 값을 읽을 필요가 없다.
        response = await session.list_tools()

        available_tools: dict[str, dict[str, Any]] = {}
        for mcp_tool in response.tools:
            available_tools[mcp_tool.name] = {
                "name": mcp_tool.name,
                "description": mcp_tool.description or "",
                "input_schema": mcp_tool.inputSchema,
            }

        return {
            "available_tools": available_tools,
            "tool_count": len(available_tools),
        }

    async def validate_tool_node(state: AgentState) -> dict[str, Any]:
        """요청한 도구가 존재하고 실행 가능한지 확인한다."""

        tool_name = state.get("tool_name", "").strip()

        # --tool을 생략하면 목록만 출력하고 종료한다.
        if not tool_name:
            return {
                "next_step": "list_only",
                "result": f"MCP 도구 {state['tool_count']}개를 조회했습니다.",
                "error": "",
            }

        if tool_name not in state["available_tools"]:
            return {
                "next_step": "reject",
                "result": "",
                "error": f"등록되지 않은 MCP 도구입니다: {tool_name}",
            }

        if is_write_tool(tool_name) and not state.get("approved", False):
            return {
                "next_step": "reject",
                "result": "",
                "error": (
                    f"{tool_name}은 변경 가능성이 있는 도구입니다. "
                    "실행하려면 --approve가 필요합니다."
                ),
            }

        return {
            "next_step": "execute",
            "result": "",
            "error": "",
        }

    async def execute_tool_node(state: AgentState) -> dict[str, str]:
        """검사를 통과한 MCP 도구를 정확한 이름으로 호출한다."""

        tool_name = state["tool_name"]
        tool_arguments = state.get("tool_arguments", {})

        try:
            call_result = await session.call_tool(
                name=tool_name,
                arguments=tool_arguments,
            )
            return {
                "result": result_to_text(call_result),
                "error": "",
            }
        except Exception as exc:  # MCP 오류를 State에 담아 사용자에게 보여 준다.
            return {
                "result": "",
                "error": f"{tool_name} 실행 실패: {exc}",
            }

    def route_after_validation(state: AgentState) -> str:
        """검사 결과에 따라 실행 또는 종료 경로를 고른다."""

        return state["next_step"]

    builder = StateGraph(AgentState)
    builder.add_node("load_tools", load_tools_node)
    builder.add_node("validate_tool", validate_tool_node)
    builder.add_node("execute_tool", execute_tool_node)

    builder.add_edge(START, "load_tools")
    builder.add_edge("load_tools", "validate_tool")
    builder.add_conditional_edges(
        "validate_tool",
        route_after_validation,
        {
            "execute": "execute_tool",
            "list_only": END,
            "reject": END,
        },
    )
    builder.add_edge("execute_tool", END)
    # 같은 프로세스 안에서 thread_id별 LangGraph 상태를 기억한다.
    # 주의: 프로그램이 종료되면 MemorySaver의 내용도 사라진다.
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


def print_tool_catalog(final_state: AgentState) -> None:
    """발견된 MCP 도구의 이름, 설명, 입력 규격을 출력한다."""

    for name, information in sorted(final_state["available_tools"].items()):
        print(f"\n[{name}]")
        print("설명:", information["description"])
        print(
            "입력:",
            json.dumps(
                information["input_schema"],
                ensure_ascii=False,
                indent=2,
            ),
        )


async def run_program(
    tool_name: str,
    tool_arguments: dict[str, Any],
    approved: bool,
    thread_id: str,
    query: str,
) -> None:
    """SPS Harness MCP에 연결한 뒤 LangGraph를 실행한다."""

    headers: dict[str, str] = {}
    if MCP_TOKEN:
        headers["Authorization"] = f"Bearer {MCP_TOKEN}"

    # 로컬 URL을 사용해도 SPS Harness가 허용한 공개 Host를 전달한다.
    mcp_host_header = os.getenv("SPS_MCP_HOST_HEADER", "")
    if mcp_host_header:
        headers["Host"] = mcp_host_header

    # 이 PC에 설치된 MCP API는 headers=를 직접 받지 않는다.
    # 따라서 인증 헤더가 들어간 httpx2 클라이언트를 http_client=로 넘긴다.
    async with (
        httpx2.AsyncClient(headers=headers) as http_client,
        streamable_http_client(
            MCP_URL,
            http_client=http_client,
        ) as streams,
    ):
        read_stream, write_stream, _ = streams

        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            graph = build_graph(session)

            # 자연어 질의에서는 Gemini가 도구를 선택하고,
            # 선택된 도구는 아래의 기존 LangGraph 검증 경로를 그대로 통과한다.
            direct_answer = ""
            if query:
                listed = await session.list_tools()
                google_catalog = {
                    item.name: {
                        "name": item.name,
                        "description": item.description or "",
                        "input_schema": item.inputSchema,
                    }
                    for item in listed.tools
                }
                tool_name, tool_arguments, direct_answer, _ = (
                    await choose_tool_with_google(query, google_catalog, approved)
                )
                if direct_answer:
                    print("\nOllama 답변:")
                    print(direct_answer)
                    return

            final_state: AgentState = await graph.ainvoke(
                {
                    "tool_name": tool_name,
                    "tool_arguments": tool_arguments,
                    "approved": approved,
                },
                {
                    "recursion_limit": 10,
                    "configurable": {"thread_id": thread_id},
                },
            )

            print(f"\n발견된 MCP 도구: {final_state['tool_count']}개")

            if not tool_name:
                print_tool_catalog(final_state)

            if final_state.get("result"):
                print("\n실행 결과:")
                print(final_state["result"])

            if final_state.get("error"):
                print("\n실행 차단 또는 오류:")
                print(final_state["error"])

            if query and final_state.get("result"):
                answer = await summarize_tool_result_with_google(
                    query,
                    tool_name,
                    tool_arguments,
                    final_state["result"],
                )
                print("\nGemini 최종 답변:")
                print(answer)


def parse_arguments_json(raw_arguments: str) -> dict[str, Any]:
    """--args 값을 JSON 객체로 검사하고 변환한다."""

    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--args JSON 형식이 잘못되었습니다: {exc}") from exc

    if not isinstance(parsed, dict):
        raise SystemExit("--args에는 JSON 객체를 입력해야 합니다. 예: '{}'")
    return parsed


def main() -> None:
    """명령행 입력을 받고 비동기 프로그램을 실행한다."""

    parser = argparse.ArgumentParser(
        description="LangGraph로 SPS Harness MCP 도구를 조회하고 호출합니다."
    )
    parser.add_argument(
        "--tool",
        default="",
        help="호출할 MCP 도구 이름. 생략하면 전체 목록을 출력합니다.",
    )
    parser.add_argument(
        "--args",
        default="{}",
        help='도구 입력 JSON. 예: \'{"key": "value"}\'',
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="변경 가능성이 있는 도구의 실행을 승인합니다.",
    )
    parser.add_argument(
        "--thread-id",
        default="sps-default",
        help="MemorySaver가 실행 상태를 구분할 세션 ID입니다.",
    )
    parser.add_argument(
        "--query",
        default="",
        help="Gemini가 필요한 MCP 도구를 선택해 답할 자연어 질문입니다.",
    )
    command = parser.parse_args()

    tool_arguments = parse_arguments_json(command.args)
    asyncio.run(
        run_program(
            tool_name=command.tool,
            tool_arguments=tool_arguments,
            approved=command.approve,
            thread_id=command.thread_id,
            query=command.query,
        )
    )


if __name__ == "__main__":
    main()
