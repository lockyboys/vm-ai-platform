"""LangGraph로 SPS Harness MCP 도구를 조회하고 이름으로 실행한다."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any, TypedDict

import httpx2
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


load_dotenv()

MCP_URL = os.getenv("SPS_MCP_URL", "http://127.0.0.1:18000/mcp")
MCP_TOKEN = os.getenv("SPS_MCP_BEARER_TOKEN", "")


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
    return builder.compile()


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
) -> None:
    """SPS Harness MCP에 연결한 뒤 LangGraph를 실행한다."""

    headers: dict[str, str] = {}
    if MCP_TOKEN:
        headers["Authorization"] = f"Bearer {MCP_TOKEN}"

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
            final_state: AgentState = await graph.ainvoke(
                {
                    "tool_name": tool_name,
                    "tool_arguments": tool_arguments,
                    "approved": approved,
                },
                {"recursion_limit": 10},
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
    command = parser.parse_args()

    tool_arguments = parse_arguments_json(command.args)
    asyncio.run(
        run_program(
            tool_name=command.tool,
            tool_arguments=tool_arguments,
            approved=command.approve,
        )
    )


if __name__ == "__main__":
    main()
