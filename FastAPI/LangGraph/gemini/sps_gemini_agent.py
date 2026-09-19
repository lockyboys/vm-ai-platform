"""FastAPI를 사용해 SPS Harness MCP 답을 구하는 LangGraph 에이전트 서버."""
# 20260913 | Codex | CommonAuth 비노출 발급·연결 점검 옵션과 CLI thread_id 추가
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict
from uuid import uuid4

PROJECT_ROOT = Path("/data/vm_project")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.errors import GraphRecursionError
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from common.common_function import logger
from common.database import CommonDatabase
from FastAPI.LangGraph.agent_memory import PersistentMemory, load_settings

load_dotenv(PROJECT_ROOT / ".env")

MCP_URL = os.getenv("SPS_MCP_URL", "http://127.0.0.1:8000/mcp")
BEARER_TOKEN = os.getenv("SPS_MCP_BEARER_TOKEN")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
AGENT_TIMEOUT_SECONDS = int(os.getenv("SPS_GEMINI_AGENT_TIMEOUT_SECONDS", "120"))
AGENT_RECURSION_LIMIT = int(os.getenv("SPS_GEMINI_AGENT_RECURSION_LIMIT", "12"))

SYSTEM_PROMPT = """
너는 SPS 개발을 지원하는 LangChain 기반 AI 에이전트다.

반드시 다음 규칙을 지킨다.

1. SPS Harness MCP 도구를 사용해 Repository와 등록 정보를 확인한다.
2. Verified SQL에 등록되지 않은 임의 SQL을 실행하지 않는다.
3. 변경 작업은 먼저 dry-run 결과를 확인한다.
4. 사용자가 명시적으로 승인하지 않은 apply 작업은 실행하지 않는다.
5. SPS의 Repository First, Metadata Driven, SSOT 원칙을 따른다.
6. 확인되지 않은 내용은 추정하지 말고 모른다고 답한다.
7. 실행 결과에는 사용한 MCP 도구와 핵심 결과를 간단히 설명한다.
"""

class ChatRequest(BaseModel):
    """Gemini 에이전트 API 요청."""

    query: str = Field(min_length=1, max_length=10000)
    thread_id: str = Field(default="sps-gemini-api", min_length=1, max_length=200)
    subject_id: str | None = Field(default=None, min_length=1, max_length=99)


class ChatResponse(BaseModel):
    """Gemini 에이전트 API 응답."""

    success: bool
    thread_id: str
    response: str
    tool_count: int


app = FastAPI(
    title="SPS Gemini LangGraph Agent",
    version="1.0.0",
    description="Gemini가 SPS Harness MCP 도구를 LangGraph를 통해 호출하는 API",
)


def validate_environment(*, require_gemini: bool = True) -> None:
    """필수 환경변수를 확인한다."""

    if not BEARER_TOKEN:
        raise RuntimeError(
            "SPS_MCP_BEARER_TOKEN 환경변수가 없습니다. "
            "먼저 export SPS_MCP_BEARER_TOKEN=\"$TOKEN\"을 실행하세요."
        )
    if len(BEARER_TOKEN.split(".")) != 3 or not all(BEARER_TOKEN.split(".")):
        raise RuntimeError("SPS_MCP_BEARER_TOKEN은 점(.)으로 나뉜 3부분의 JWT여야 합니다.")
    if require_gemini and not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY 환경변수가 없습니다. Gemini API 키를 설정하세요.")


def issue_common_auth_token(user_id: str) -> None:
    """명시한 사용자로 발급하고 현재 프로세스의 토큰만 교체합니다.

    실행하는 서버의 CommonAuth 환경설정을 사용합니다. 토큰은 출력하거나
    파일에 저장하지 않으며, 부모 터미널의 환경변수는 변경할 수 없습니다.
    """
    if not user_id.strip():
        raise ValueError("CommonAuth 사용자 ID가 비어 있습니다.")
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from common.auth import CommonAuth

    auth = CommonAuth()
    token = auth.issue_access_token(user_id.strip())
    auth.verify_token(token, expected_type="access")
    global BEARER_TOKEN
    BEARER_TOKEN = token
    os.environ["SPS_MCP_BEARER_TOKEN"] = token


def create_mcp_client() -> MultiServerMCPClient:
    """SPS Harness MCP Streamable HTTP 클라이언트를 생성한다."""

    return MultiServerMCPClient(
        {
            "sps_harness": {
                "transport": "streamable_http",
                "url": MCP_URL,
                "headers": {
                    "Authorization": f"Bearer {BEARER_TOKEN}",
                    "Accept": "application/json, text/event-stream",
                },
            }
        }
    )


def create_gemini_model() -> ChatGoogleGenerativeAI:
    """Gemini LangChain 모델을 생성한다."""

    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=0,
        max_retries=2,
    )


class SimpleState(TypedDict, total=False):
    """LangGraph 실행 상태."""

    messages: Annotated[list[Any], add_messages]
    thread_id: str


def build_graph(model: ChatGoogleGenerativeAI, tools: list[Any]):
    """Gemini와 SPS Harness MCP 도구를 명시적 LangGraph로 연결한다."""

    model_with_tools = model.bind_tools(tools)

    async def rag_node(state: SimpleState) -> dict[str, list[Any]]:
        response = await model_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    async def verifier(state: SimpleState) -> dict[str, list[Any]]:
        verification_prompt = (
            "앞선 대화 내용 중 MCP 도구 호출 결과가 있다면 SPS 원칙(Verified SQL, SSOT, 변경 전 dry-run 등)에 맞는지 검증하고 사실만 간결히 정리해라. "
            "만약 단순 인사나 일반 질문이라 MCP 조회가 필요 없는 경우라면, 사용자의 질문에 맞춰 친절하고 자연스럽게 응답을 완성해라. "
            "확인되지 않은 시스템 사실을 임의로 지어내지만 말아라."
        )
        response = await model.ainvoke(
            [*state["messages"], HumanMessage(content=verification_prompt)]
        )
        return {"messages": [response]}

    builder = StateGraph(SimpleState)
    builder.add_node("rag_node", rag_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("verifier", verifier)
    builder.add_edge(START, "rag_node")
    builder.add_conditional_edges(
        "rag_node",
        tools_condition,
        {"tools": "tools", "__end__": "verifier"},
    )
    builder.add_edge("tools", "rag_node")
    builder.add_edge("verifier", END)
    return builder.compile(checkpointer=MemorySaver())


async def create_agent() -> tuple[Any, int]:
    """SPS Harness MCP 도구를 연결한 LangGraph를 생성한다."""

    validate_environment()
    client = create_mcp_client()
    tools = await client.get_tools()
    return build_graph(create_gemini_model(), tools), len(tools)


def create_long_term_memory() -> PersistentMemory:
    """CommonDatabase를 통해 MongoDB 장기기억 저장소를 생성한다."""
    settings = load_settings()
    settings["database_role"] = os.getenv(
        "SPS_AGENT_MEMORY_DATABASE_ROLE",
        settings["database_role"],
    )
    settings["collection_name"] = os.getenv(
        "SPS_AGENT_MEMORY_COLLECTION",
        settings["collection_name"],
    )
    database = CommonDatabase(
        database_role=settings["database_role"],
        connect_mariadb=False,
        connect_mongodb=True,
    )
    return PersistentMemory(settings=settings, database=database)


async def recall_long_term_memory(
    memory: PersistentMemory,
    subject_id: str | None,
    thread_id: str,
    query: str,
) -> str:
    if not subject_id:
        return ""
    return await asyncio.to_thread(memory.recall, subject_id, thread_id, query)


async def save_long_term_memory(
    memory: PersistentMemory,
    subject_id: str | None,
    thread_id: str,
    query: str,
    response: str,
) -> None:
    if not subject_id:
        return
    await asyncio.to_thread(
        memory.save,
        subject_id,
        thread_id,
        uuid4().hex,
        query,
        {"response": response, "token_usage": {}},
        os.getenv("SPS_AGENT_CLIENT_IP", "127.0.0.1"),
    )
    logger.info(
        "Long-term memory saved: subject_id=%s thread_id=%s collection=%s",
        subject_id,
        thread_id,
        memory.collection,
    )


def extract_message_content(content: Any) -> str:
    """LangChain 메시지 content를 출력 문자열로 변환한다."""

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


async def invoke_agent(
    query: str,
    thread_id: str,
    subject_id: str | None = None,
) -> tuple[str, int]:
    """요청 1건을 LangGraph 에이전트로 실행한다."""

    agent, tool_count = await create_agent()
    memory = create_long_term_memory() if subject_id else None
    recalled = await recall_long_term_memory(memory, subject_id, thread_id, query) if memory else ""
    user_content = query
    if recalled:
        user_content = (
            "다음은 같은 사용자의 과거 장기기억이다. 현재 질문과 관련된 경우에만 참고해라.\n"
            f"{recalled}\n\n현재 질문: {query}"
        )
    try:
        result = await asyncio.wait_for(
            agent.ainvoke(
                {
                    "messages": [
                        SystemMessage(content=SYSTEM_PROMPT),
                        HumanMessage(content=user_content),
                    ],
                    "thread_id": thread_id,
                },
                config={
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": AGENT_RECURSION_LIMIT,
                },
            ),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except GraphRecursionError:
        return (
            "MCP 도구 호출이 반복되어 안전하게 중단했습니다. "
            "조회 범위를 한 가지로 좁혀 다시 요청해 주세요.",
            tool_count,
        )
    messages = result.get("messages", [])
    if not messages:
        raise RuntimeError("Gemini 응답이 없습니다.")
    content = extract_message_content(getattr(messages[-1], "content", messages[-1]))
    if memory:
        await save_long_term_memory(memory, subject_id, thread_id, query, content)
    return content, tool_count


@app.get("/health")
async def health() -> dict[str, str]:
    """API 프로세스 상태만 확인한다."""

    return {"status": "ok", "service": "sps-gemini-agent"}


@app.post("/api/gemini/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Gemini가 필요할 때 SPS Harness MCP 도구를 선택·호출한다."""

    try:
        response, tool_count = await invoke_agent(
            request.query,
            request.thread_id,
            request.subject_id,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini 또는 SPS Harness MCP 호출에 실패했습니다: {type(exc).__name__}",
        ) from exc
    return ChatResponse(
        success=True,
        thread_id=request.thread_id,
        response=response,
        tool_count=tool_count,
    )


def get_user_query(arguments: list[str] | None = None) -> str:
    """명령행 인자 또는 기본 질의를 반환한다."""

    arguments = sys.argv[1:] if arguments is None else arguments
    if arguments:
        return " ".join(arguments).strip()
    return "SPS Harness MCP에 연결되었는지 확인하고, 사용 가능한 MCP 도구의 이름과 역할을 설명해줘."


async def run_agent(
    user_query: str,
    thread_id: str = "sps-gemini-cli",
    subject_id: str | None = None,
) -> None:
    """MCP 도구를 Gemini LangGraph 에이전트에 연결해 실행한다."""

    validate_environment()
    print(f"[*] 랭체인 MCP 클라이언트 연결 시도 (Streamable HTTP): {MCP_URL}")
    client = create_mcp_client()
    tools = await client.get_tools()
    print(f"[+] SPS Harness MCP 도구 {len(tools)}개 로드 완료")
    for tool in tools:
        print(f"    - {getattr(tool, 'name', 'unknown')}")
    agent = build_graph(create_gemini_model(), tools)
    memory = create_long_term_memory() if subject_id else None
    recalled = await recall_long_term_memory(memory, subject_id, thread_id, user_query) if memory else ""
    user_content = user_query
    if recalled:
        user_content = (
            "다음은 같은 사용자의 과거 장기기억이다. 현재 질문과 관련된 경우에만 참고해라.\n"
            f"{recalled}\n\n현재 질문: {user_query}"
        )
    try:
        result = await asyncio.wait_for(
            agent.ainvoke(
                {
                    "messages": [
                        SystemMessage(content=SYSTEM_PROMPT),
                        HumanMessage(content=user_content),
                    ]
                },
                config={
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": AGENT_RECURSION_LIMIT,
                },
            ),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except GraphRecursionError:
        print("[Gemini 응답]")
        print("MCP 도구 호출이 반복되어 안전하게 중단했습니다. 조회 범위를 한 가지로 좁혀 다시 요청해 주세요.")
        return
    messages = result.get("messages", [])
    if not messages:
        print("[!] Gemini 응답이 없습니다.")
        return
    response = extract_message_content(getattr(messages[-1], "content", messages[-1]))
    if memory:
        await save_long_term_memory(memory, subject_id, thread_id, user_query, response)
    print("[Gemini 응답]")
    print(response)


async def main() -> None:
    parser = argparse.ArgumentParser(description="SPS Gemini LangGraph 에이전트")
    parser.add_argument("query", nargs="*", help="Gemini에게 전달할 질문")
    parser.add_argument("--thread-id", default="sps-gemini-cli")
    parser.add_argument("--common-auth-user", metavar="USER_ID", help="서버의 CommonAuth 설정으로 토큰을 비노출 발급")
    parser.add_argument("--check-mcp", action="store_true", help="Gemini 호출 없이 MCP 인증과 도구 목록 조회만 점검")
    args = parser.parse_args()
    try:
        if args.common_auth_user:
            issue_common_auth_token(args.common_auth_user)
            print("CommonAuth 토큰 발급·현재 프로세스 설정 완료 (원문 비노출)")
        if args.check_mcp:
            validate_environment(require_gemini=False)
            loaded_tools = await asyncio.wait_for(create_mcp_client().get_tools(), timeout=20)
            print(f"MCP_OK tools={len(loaded_tools)}")
        else:
            await run_agent(
                get_user_query(args.query),
                thread_id=args.thread_id,
                subject_id=args.common_auth_user or os.getenv("SPS_AGENT_SUBJECT_ID"),
            )
    except Exception as error:
        # 원문 예외 메시지에는 자격증명이 포함될 수 있으므로 종류와 HTTP 코드만 출력합니다.
        pending = [error]
        details: list[str] = []
        while pending:
            current = pending.pop()
            children = getattr(current, "exceptions", ())
            if children:
                pending.extend(children)
                continue
            status = getattr(getattr(current, "response", None), "status_code", None)
            details.append(f"HTTP {status}" if status is not None else type(current).__name__)
        print("MCP_AGENT_FAILED: " + ", ".join(sorted(set(details))), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    asyncio.run(main())
