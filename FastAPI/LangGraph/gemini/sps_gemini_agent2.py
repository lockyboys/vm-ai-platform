"""FastAPI를 사용해 SPS Harness MCP 답을 구하는 LangGraph 에이전트 서버."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

PROJECT_ROOT = Path("/data/vm_project")
load_dotenv(PROJECT_ROOT / ".env")

# 1. 동적 토큰 생성 함수
def get_bearer_token() -> str:
    """CommonAuth를 통해 유효한 새 액세스 토큰을 즉시 발급한다."""
    try:
        from common.auth import CommonAuth
        token = CommonAuth().issue_access_token("jeaje")
        if token:
            return token
    except Exception as e:
        print(f"[!] CommonAuth 발급 경고: {e}")
    return os.getenv("SPS_MCP_BEARER_TOKEN", "")

# 로컬 GCP VM 환경이므로 127.0.0.1 직접 접속을 기본으로 설정
MCP_URL = os.getenv("SPS_MCP_URL", "http://127.0.0.1:8000/mcp")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

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
    query: str = Field(min_length=1, max_length=10000)
    thread_id: str = Field(default="sps-gemini-api", min_length=1, max_length=200)

class ChatResponse(BaseModel):
    success: bool
    thread_id: str
    response: str
    tool_count: int

app = FastAPI(title="SPS Gemini LangGraph Agent", version="1.0.0")

def validate_environment() -> str:
    token = get_bearer_token()
    if not token or len(token) < 20:
        raise RuntimeError("유효한 Bearer 토큰을 생성할 수 없습니다.")
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY 환경변수가 없습니다.")
    return token

def create_mcp_client(token: str) -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {
            "sps_harness": {
                "transport": "streamable_http",
                "url": MCP_URL,
                "headers": {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json, text/event-stream",
                    "ngrok-skip-browser-warning": "true",
                },
            }
        }
    )

def create_gemini_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=0,
        max_retries=2,
    )

class SimpleState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    thread_id: str

def build_graph(model: ChatGoogleGenerativeAI, tools: list[Any]):
    model_with_tools = model.bind_tools(tools)

    async def rag_node(state: SimpleState) -> dict[str, list[Any]]:
        response = await model_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    async def verifier(state: SimpleState) -> dict[str, list[Any]]:
        verification_prompt = (
            "앞선 MCP 조회 결과와 Gemini 답변을 SPS 원칙에 맞게 검증하고 "
            "확인된 사실만 간결하게 정리해라. 확인되지 않은 내용은 모른다고 밝혀라."
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
    token = validate_environment()
    client = create_mcp_client(token)
    tools = await client.get_tools()
    return build_graph(create_gemini_model(), tools), len(tools)

def extract_message_content(content: Any) -> str:
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

def get_user_query() -> str:
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()
    return "SPS Harness MCP에 연결되었는지 확인하고, 사용 가능한 MCP 도구의 이름과 역할을 설명해줘."

async def run_agent(user_query: str) -> None:
    token = validate_environment()
    print(f"[*] 랭체인 MCP 클라이언트 연결 시도 (Streamable HTTP): {MCP_URL}")
    client = create_mcp_client(token)
    tools = await client.get_tools()
    print(f"[+] SPS Harness MCP 도구 {len(tools)}개 로드 완료")
    for tool in tools:
        print(f"    - {getattr(tool, 'name', 'unknown')}")
    
    agent = build_graph(create_gemini_model(), tools)
    result = await agent.ainvoke(
        {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_query),
            ]
        }
    )
    messages = result.get("messages", [])
    if not messages:
        print("[!] Gemini 응답이 없습니다.")
        return
    print("\n[Gemini 응답]")
    print(extract_message_content(getattr(messages[-1], "content", messages[-1])))

async def main() -> None:
    await run_agent(get_user_query())

if __name__ == "__main__":
    asyncio.run(main())