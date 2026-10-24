# /data/vm_project/venv/bin/python /data/vm_project/FastAPI/LangGraph/gemini/sps_gemini_agent.py
# 
"""FastAPI를 사용해 SPS Harness MCP 및 Gmail API 답을 구하는 대화형 에이전트 서버."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import traceback
import jwt
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Annotated, Any, TypedDict
from uuid import uuid4
from email.mime.text import MIMEText

PROJECT_ROOT = Path("/data/vm_project")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.errors import GraphRecursionError
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

load_dotenv(PROJECT_ROOT / ".env")

# 목적: CommonAuth가 보호된 서비스 환경의 공유 서명 키를 읽게 합니다.
# 주의: 소스 기본 키를 두지 않으며, 키가 없으면 CommonAuth가 실패 처리합니다.

from common.auth import CommonAuth

MCP_URL = os.getenv("SPS_MCP_URL", "https://subprime-glowworm-mundane.ngrok-free.dev/mcp")
MCP_HOST_HEADER = os.getenv("SPS_MCP_HOST_HEADER")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
AGENT_TIMEOUT_SECONDS = int(os.getenv("SPS_GEMINI_AGENT_TIMEOUT_SECONDS", "120"))
AGENT_RECURSION_LIMIT = int(os.getenv("SPS_GEMINI_AGENT_RECURSION_LIMIT", "12"))

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

SYSTEM_PROMPT = """
너는 SPS 개발을 지원하는 LangChain 기반 AI 비서(Agent)다.
1. SPS Harness MCP 도구를 사용해 Repository와 등록 정보를 확인한다.
2. Verified SQL에 등록되지 않은 임의 SQL을 실행하지 않는다.
3. 메일(Gmail) 조회 및 발송 명령이 떨어지면 read_recent_emails 및 send_gmail 도구를 적극 활용하여 사용자를 돕는다.
"""

def generate_and_inject_jwt(user_id: str = "jeaje") -> str:
    auth = CommonAuth()
    token = auth.issue_access_token(user_id)
    os.environ["SPS_MCP_BEARER_TOKEN"] = token
    return token

def create_mcp_client() -> MultiServerMCPClient:
    token = os.environ.get("SPS_MCP_BEARER_TOKEN")
    if not token: raise RuntimeError("토큰이 주입되지 않았습니다.")
    auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
    headers = {
        "Authorization": auth_header,
        "Accept": "application/json, text/event-stream",
        "ngrok-skip-browser-warning": "true",
        "User-Agent": "SPS-Gemini-Agent/1.0"
    }
    if MCP_HOST_HEADER: headers["Host"] = MCP_HOST_HEADER
    return MultiServerMCPClient({"sps_harness": {"transport": "streamable_http", "url": MCP_URL, "headers": headers}})

# ==========================================
# Gmail API 도구 (대표님 제공 코드 통합)
# ==========================================
def get_gmail_service() -> Resource:
    creds = None
    token_path = PROJECT_ROOT / "token.json"
    creds_path = PROJECT_ROOT / "credentials.json"

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise FileNotFoundError(f"{creds_path} 파일이 없습니다. Google Cloud Console에서 발급받아 서버 루트에 넣어주세요.")
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def _extract_body(payload: dict) -> str:
    body_data = ""
    parts = payload.get("parts", [])
    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"].encode("ASCII")).decode("utf-8", errors="replace")
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"].encode("ASCII")).decode("utf-8", errors="replace")
        elif "parts" in part:
            nested = _extract_body(part)
            if nested: return nested
    return body_data

@tool
def read_recent_emails(max_results: int = 3) -> str:
    """최근 Gmail 목록을 조회하고 파싱하여 요약 정보를 반환합니다."""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId="me", maxResults=max_results).execute()
        messages = results.get("messages", [])
        if not messages: return "조회된 메일이 없습니다."

        output = [f"📬 최근 이메일 {len(messages)}건 조회 결과:"]
        for idx, msg_meta in enumerate(messages, start=1):
            msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
            payload = msg.get("payload", {})
            headers = {h["name"].lower(): h["value"] for h in payload.get("headers", []) if h["name"].lower() in ["from", "to", "subject", "date"]}
            body = _extract_body(payload)
            output.append(f"\n[메일 #{idx}] 제목: {headers.get('subject', '제목 없음')} / 보낸사람: {headers.get('from', 'N/A')}\n본문: {body.strip()[:200]}...")
        return "\n".join(output)
    except Exception as e:
        return f"❌ 메일 조회 실패: {str(e)}"

@tool
def send_gmail(recipient: str, subject: str, content: str) -> str:
    """지정된 수신자에게 이메일을 발송합니다."""
    try:
        service = get_gmail_service()
        message = MIMEText(content, _charset="utf-8")
        message["to"] = recipient
        message["from"] = "me"
        message["subject"] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        sent_message = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
        return f"✅ 메일 전송 성공 (ID: {sent_message.get('id')})"
    except Exception as e:
        return f"❌ 메일 전송 실패: {str(e)}"

# ==========================================
# 에이전트 설정 및 실행
# ==========================================
def create_gemini_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0, max_retries=2)

class SimpleState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    thread_id: str

def build_graph(model: ChatGoogleGenerativeAI, tools: list[Any]):
    model_with_tools = model.bind_tools(tools)
    
    async def rag_node(state: SimpleState) -> dict[str, list[Any]]:
        return {"messages": [await model_with_tools.ainvoke(state["messages"])]}
        
    async def verifier(state: SimpleState) -> dict[str, list[Any]]:
        return {"messages": [await model.ainvoke([*state["messages"], HumanMessage(content="결과를 사용자에게 깔끔하게 요약해줘.")])]}
        
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
    client = create_mcp_client()
    mcp_tools = await client.get_tools()
    # 💡 서버 MCP 도구 49개 + 방금 합친 Gmail 도구 2개를 묶어버립니다!
    all_tools = mcp_tools + [read_recent_emails, send_gmail]
    return build_graph(create_gemini_model(), all_tools), len(all_tools)

def extract_message_content(content: Any) -> str:
    if isinstance(content, str): return content
    if isinstance(content, list):
        return "\n".join([item["text"] if isinstance(item, dict) and "text" in item else str(item) for item in content])
    return str(content)

async def main() -> None:
    try:
        generate_and_inject_jwt("jeaje")
        agent, tool_count = await create_agent()
        
        print("\n" + "="*60)
        print(f"🤖 [SPS AI Agent 가동] MCP 도구 + Gmail 도구 총 {tool_count}개 장착 완료!")
        print("💡 팁: '최근 메일 3개 읽어줘', '쿼리 목록 조회해줘' 등 자유롭게 명령하세요.")
        print("   (종료하시려면 'quit' 또는 'exit' 입력)")
        print("="*60)
        
        thread_id = str(uuid4())
        while True:
            user_input = input("\n👤 Luckyboys 대표님: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 에이전트를 종료합니다.")
                break
            if not user_input: continue
                
            print("🤖 에이전트가 도구를 사용해 명령을 수행 중입니다...")
            result = await asyncio.wait_for(
                agent.ainvoke(
                    {"messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_input)], "thread_id": thread_id},
                    config={"configurable": {"thread_id": thread_id}, "recursion_limit": AGENT_RECURSION_LIMIT},
                ), timeout=AGENT_TIMEOUT_SECONDS
            )
            messages = result.get("messages", [])
            print(f"\n💡 [Gemini]:\n{extract_message_content(getattr(messages[-1], 'content', messages[-1]))}")
            
    except Exception as error:
        print("\n[🚨 실행 중 에러 발생!]")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
