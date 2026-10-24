# export SPS_AUTH_JWT_EXPIRE_SECONDS=900 SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS=86400
# sudo systemctl show sps-harness.service --property=Environment | grep SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS
# /data/vm_project/venv/bin/python /data/vm_project/FastAPI/LangGraph/gemini/sps_gemini_agent.py --common-auth-user jeaje --check-mcp
# 확인 항목	             결과	                                    상태 => 결과 확인
# CommonAuth 토큰	    발급·현재 프로세스 적용 확인(원문 비노출)	    확인    
# SPS Harness MCP 연결	MCP_OK tools=41	                          정상 연결 완료
# python /data/vm_project/FastAPI/LangGraph/gemini/sps_gemini_agent.py --common-auth-user jeaje "table_schema 도구로 verified_sql 관련 테이블 스키마를 직접 조회하고 결과를 표로 출력해줘"
# 20260913 | Codex | CommonAuth 비노출 발급·연결 점검 옵션과 CLI thread_id 추가
# sps_gemini_agent.py
# export SPS_AUTH_JWT_EXPIRE_SECONDS=900 SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS=86400
# sudo systemctl show sps-harness.service --property=Environment | grep SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS
#/data/vm_project/venv/bin/python /data/vm_project/FastAPI/LangGraph/gemini/sps_gemini_agent.py "서버에 연결되었는지 확인해 줘"
"""FastAPI를 사용해 SPS Harness MCP 답을 구하는 LangGraph 에이전트 서버."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import Annotated, Any, TypedDict
from uuid import uuid4

PROJECT_ROOT = Path("/data/vm_project")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# 목적: CommonAuth가 보호된 서비스 환경의 공유 서명 키를 읽게 합니다.
# 주의: 소스 기본 키를 두지 않으며, 키가 없으면 CommonAuth가 실패 처리합니다.

# 💡 공식 팩토리 로드
from common.auth import CommonAuth
from common.common_function import logger
from common.database import CommonDatabase, MariaMongoWriteService
from FastAPI.LangGraph.agent_memory import PersistentMemory, load_settings

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

MCP_URL = os.getenv("SPS_MCP_URL", "https://subprime-glowworm-mundane.ngrok-free.dev/mcp")
MCP_HOST_HEADER = os.getenv("SPS_MCP_HOST_HEADER")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
AGENT_TIMEOUT_SECONDS = int(os.getenv("SPS_GEMINI_AGENT_TIMEOUT_SECONDS", "120"))
AGENT_RECURSION_LIMIT = int(os.getenv("SPS_GEMINI_AGENT_RECURSION_LIMIT", "12"))

SYSTEM_PROMPT = """
너는 SPS 개발을 지원하는 LangChain 기반 AI 에이전트다.
1. SPS Harness MCP 도구를 사용해 Repository와 등록 정보를 확인한다.
2. Verified SQL에 등록되지 않은 임의 SQL을 실행하지 않는다.
"""

def generate_and_inject_jwt(user_id: str = "jeaje") -> str:
    """서버와 100% 동일한 로직(CommonAuth)으로 토큰을 발급합니다."""
    auth = CommonAuth()
    token = auth.issue_access_token(user_id)
    os.environ["SPS_MCP_BEARER_TOKEN"] = token
    print("✅ [인증 완료] 서버 공식 모듈(CommonAuth)을 사용해 진짜 토큰 발급 성공")
    return token

def create_mcp_client() -> MultiServerMCPClient:
    token = os.environ.get("SPS_MCP_BEARER_TOKEN")
    if not token:
        raise RuntimeError("토큰이 주입되지 않았습니다.")
        
    auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
        
    headers = {
        "Authorization": auth_header,
        "Accept": "application/json, text/event-stream",
        "ngrok-skip-browser-warning": "true",
        "User-Agent": "SPS-Gemini-Agent/1.0"
    }
    
    if MCP_HOST_HEADER:
        headers["Host"] = MCP_HOST_HEADER

    return MultiServerMCPClient({
        "sps_harness": {
            "transport": "streamable_http",
            "url": MCP_URL,
            "headers": headers,
        }
    })

def create_gemini_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0, max_retries=2)

class SimpleState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    thread_id: str

def build_graph(model: ChatGoogleGenerativeAI, tools: list[Any]):
    model_with_tools = model.bind_tools(tools)
    
    async def rag_node(state: SimpleState) -> dict[str, list[Any]]:
        response = await model_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}
        
    async def verifier(state: SimpleState) -> dict[str, list[Any]]:
        response = await model.ainvoke([*state["messages"], HumanMessage(content="결과를 사용자에게 깔끔하게 요약해줘.")])
        return {"messages": [response]}
        
    builder = StateGraph(SimpleState)
    builder.add_node("rag_node", rag_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("verifier", verifier)
    builder.add_edge(START, "rag_node")
    builder.add_conditional_edges("rag_node", tools_condition, {"tools": "tools", "__end__": "verifier"})
    builder.add_edge("tools", "rag_node")
    builder.add_edge("verifier", END)
    return builder.compile(checkpointer=MemorySaver())

async def create_agent() -> tuple[Any, int]:
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY 환경변수가 없습니다.")
    client = create_mcp_client()
    tools = await client.get_tools()
    return build_graph(create_gemini_model(), tools), len(tools)

def extract_message_content(content: Any) -> str:
    if isinstance(content, str): return content
    if isinstance(content, list):
        return "\n".join([item["text"] if isinstance(item, dict) and "text" in item else str(item) for item in content])
    return str(content)

async def invoke_agent(query: str, thread_id: str) -> tuple[str, int]:
    agent, tool_count = await create_agent()
    try:
        result = await asyncio.wait_for(
            agent.ainvoke(
                {"messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=query)], "thread_id": thread_id},
                config={"configurable": {"thread_id": thread_id}, "recursion_limit": AGENT_RECURSION_LIMIT},
            ), timeout=AGENT_TIMEOUT_SECONDS
        )
    except GraphRecursionError:
        return "MCP 도구 호출 반복 중단", tool_count
        
    messages = result.get("messages", [])
    if not messages:
        raise RuntimeError("Gemini 응답이 없습니다.")
    return extract_message_content(getattr(messages[-1], "content", messages[-1])), tool_count

async def main() -> None:
    parser = argparse.ArgumentParser(description="SPS Gemini LangGraph 에이전트")
    parser.add_argument("query", nargs="*", help="Gemini에게 전달할 질문")
    parser.add_argument("--thread-id", default="sps-gemini-cli")
    parser.add_argument("--common-auth-user", default="jeaje", help="서버 통과용 인증 계정")
    args, _ = parser.parse_known_args()
    
    query_text = " ".join(args.query) if args.query else "서버에 연결되었는지 확인하고, 사용 가능한 도구 목록을 알려줘."
    
    try:
        # 1. 완벽한 형태의 공식 토큰 발급
        generate_and_inject_jwt(args.common_auth_user)
        print(f"[*] 랭체인 MCP 클라이언트 연결 시도: {MCP_URL}")
        
        # 2. 에이전트 실행
        response, tool_count = await invoke_agent(query_text, args.thread_id)
        
        print(f"\n[+] SPS Harness MCP 도구 {tool_count}개 로드 및 실행 완료")
        print("="*50)
        print("[Gemini 응답]")
        print(response)
        print("="*50)
        
    except Exception as error:
        print("\n[🚨 실행 중 에러 발생!]")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())