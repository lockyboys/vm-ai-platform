# /data/vm_project/FastAPI/LangGraph/gemini/sps_gemini_agent.py
# 
"""FastAPI를 사용해 SPS Harness MCP 및 Gmail API 답을 구하는 대화형 에이전트 서버."""
from __future__ import annotations

import os
import sys
import base64
from pathlib import Path
from typing import Annotated, Any, TypedDict
from uuid import uuid4
from email.mime.text import MIMEText

# FastAPI 관련 임포트 추가
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

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

MCP_URL = os.getenv("SPS_MCP_URL", "http://127.0.0.1:8000/mcp")
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

# FastAPI 앱 객체 선언
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

app = FastAPI(title="SPS Agent Gateway Server")

# 전역 에이전트 및 도구 관리를 위한 변수
agent_instance = None

def generate_and_inject_jwt(user_id: str = "jeaje") -> str:
    auth = CommonAuth()
    token = auth.issue_access_token(user_id)
    os.environ["SPS_MCP_BEARER_TOKEN"] = token
    return token

def create_mcp_client() -> MultiServerMCPClient:
    token = generate_and_inject_jwt("jeaje")
    headers = {
        "Host": "subprime-glowworm-mundane.ngrok-free.dev",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "SPS-Gemini-Agent/1.0"
    }
    return MultiServerMCPClient({"sps_harness": {"transport": "streamable_http", "url": MCP_URL, "headers": headers}})

# ==========================================
# Gmail API 도구
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
                raise FileNotFoundError(f"{creds_path} 파일이 없습니다.")
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
# 에이전트 설정
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

async def create_agent():
    client = create_mcp_client()
    mcp_tools = await client.get_tools()
    all_tools = mcp_tools + [read_recent_emails, send_gmail]
    return build_graph(create_gemini_model(), all_tools)

def extract_message_content(content: Any) -> str:
    if isinstance(content, str): return content
    if isinstance(content, list):
        return "\n".join([item["text"] if isinstance(item, dict) and "text" in item else str(item) for item in content])
    return str(content)

# ==========================================
# FastAPI HTTP 엔드포인트 정의
# ==========================================

class MailSendRequest(BaseModel):
    recipient: str
    subject: str
    content: str

class ChatRequest(BaseModel):
    user_input: str

@app.on_event("startup")
async def startup_event():
    """서버 기동 시 에이전트 및 JWT 자동 준비"""
    global agent_instance
    try:
        generate_and_inject_jwt("jeaje")
        agent_instance = await create_agent()
        print("🤖 [SPS AI Agent] FastAPI 기동 및 에이전트 로드 성공!")
    except Exception as e:
        print(f"❌ 초기화 실패: {str(e)}")

@app.get("/gmail/read")
async def api_read_recent_emails(max_results: int = Query(default=3)):
    """최근 이메일 읽기 엔드포인트"""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, read_recent_emails.invoke, {"max_results": max_results})
        return {"result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gmail/send")
async def api_send_gmail(req: MailSendRequest):
    """이메일 전송 엔드포인트"""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, send_gmail.invoke, {
            "recipient": req.recipient,
            "subject": req.subject,
            "content": req.content
        })
        return {"result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/chat")
async def api_chat_agent(req: ChatRequest):
    """에이전트와의 대화 및 도구 사용 엔드포인트"""
    global agent_instance
    if not agent_instance:
        raise HTTPException(status_code=503, detail="에이전트가 로드되지 않았습니다.")
    try:
        import asyncio
        thread_id = str(uuid4())
        result = await asyncio.wait_for(
            agent_instance.ainvoke(
                {
                    "messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=req.user_input)], 
                    "thread_id": thread_id
                },
                config={"configurable": {"thread_id": thread_id}, "recursion_limit": AGENT_RECURSION_LIMIT},
            ), timeout=AGENT_TIMEOUT_SECONDS
        )
        messages = result.get("messages", [])
        return {"result": extract_message_content(getattr(messages[-1], 'content', messages[-1]))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("sps_gemini_agent:app", host="0.0.0.0", port=8012, reload=True)
