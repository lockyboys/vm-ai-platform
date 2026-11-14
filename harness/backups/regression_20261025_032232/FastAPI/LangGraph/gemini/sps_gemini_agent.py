# /data/vm_project/FastAPI/LangGraph/gemini/sps_gemini_agent.py
# 
"""FastAPI를 사용해 SPS Harness MCP 및 Gmail API 답을 구하는 대화형 에이전트 서버."""
from __future__ import annotations
from contextlib import asynccontextmanager

import os
import sys
import base64
import asyncio
import traceback
import httpx
from starlette.requests import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse
from pathlib import Path
from typing import Annotated, Any, TypedDict
from uuid import uuid4
from email.mime.text import MIMEText

# FastAPI 관련 임포트 추가
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
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

from common.auth import AuthenticationError, CommonAuth

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

MCP_AUTH_SERVER_URL = "http://127.0.0.1:8000"


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


# --- lifespan 이벤트 (초기화 오류 방지) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("🔥 FastAPI 앱 초기화 시작...")
    except Exception as e:
        print(f"⚠️ 초기화 오류 무시 (서버 기동 유지): {e}")
    yield
    print("🔥 FastAPI 앱 종료...")

app = FastAPI(title="SPS Agent Gateway Server", lifespan=lifespan)

# 전역 에이전트 및 도구 관리를 위한 변수
agent_instance = None

def generate_and_inject_jwt(user_id: str = "jeaje") -> str:
    auth = CommonAuth()
    token = auth.issue_access_token(user_id)
    os.environ["SPS_MCP_BEARER_TOKEN"] = token
    return token

def create_mcp_client() -> MultiServerMCPClient:
    # 프로세스 시작 시 주입된 토큰은 만료·회전됐을 수 있어 MCP 연결마다 새로 발급합니다.
    # 발급은 CommonAuth 환경 설정을 사용하며 비밀값이나 토큰을 로그에 남기지 않습니다.
    token = generate_and_inject_jwt()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "SPS-Gemini-Agent/1.0"
    }
    return MultiServerMCPClient({
        "sps_harness": {
            "transport": "streamable_http",
            "url": "http://127.0.0.1:8000/mcp",
            "headers": headers
        }
    })


# ==========================================
# 에이전트 인스턴스 안전 로드 함수
# 청크/스트림 대응 안전한 에이전트 빌더 2026.10.13
# ==========================================
async def get_or_create_agent():
    global agent_instance
    if agent_instance is not None:
        return agent_instance
    
    print("🔄 에이전트 빌드 시작...")
    mcp_tools = []

    try:
        # 충분한 여유(10초)를 두고 청크/스트림 도구 스키마를 온전히 수신
        client = create_mcp_client()
        mcp_tools = await asyncio.wait_for(client.get_tools(), timeout=10.0)
        print(f"🎉 [성공] 총 {len(mcp_tools)}개의 SPS Harness MCP 도구를 정상 장착했습니다!")
    except Exception as e:
        # TaskGroup 예외의 하위 원인만 기록하며 인증 헤더·토큰은 출력하지 않습니다.
        traceback.print_exception(type(e), e, e.__traceback__)
        print(f"⚠️ [주의] MCP 도구 수신 지연/실패 ({e}), 우선 기본 Gmail 도구로 작동합니다.")

    all_tools = mcp_tools + [read_recent_emails, send_gmail]
    print(f"🛠️ [최종 상태] 에이전트에 바인딩된 총 도구 수: {len(all_tools)}개")

    # 2. Gmail 기본 도구 탑재
    all_tools = mcp_tools + [read_recent_emails, send_gmail]
    agent_instance = build_graph(create_gemini_model(), all_tools)
    print("🤖 [SPS AI Agent] 에이전트 준비 완료!")

    agent_instance = build_graph(create_gemini_model(), all_tools)
    return agent_instance

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

# ==============================================================================
# [참고: 방법 C] FastAPI 서버 구동 시 토큰 수동 발급/만료 문제를 없애는 최소 코드 보강안
# - 대상 파일: /data/vm_project/FastAPI/LangGraph/gemini/sps_gemini_agent.py
# - 목적: API 호출 시마다 subject_id(또는 기본 계정)로 토큰을 자동 갱신하여
#         900초 만료나 환경변수 누락 없이 SPS Harness MCP에 항상 접근하도록 보장합니다.
# - 주의점: 원본 보존 원칙에 따라 필요하실 때만 invoke_agent() 상단에 2줄을 추가하세요.
# ==============================================================================

async def invoke_agent(
    query: str,
    thread_id: str,
    subject_id: str | None = None,
) -> tuple[str, int]:
    """요청 1건을 LangGraph 에이전트로 실행한다."""

    # [추가] API 모드에서도 매 요청 시 유효한 CommonAuth 토큰을 자동 발급·적용 (900초 만료 방지)
    auth_user = subject_id or os.getenv("SPS_AGENT_SUBJECT_ID", "jeaje")
    issue_common_auth_token(auth_user)

    # 기존 로직 동일: 환경변수 검증 후 MCP 클라이언트 생성 및 48개 도구 로드
    agent, tool_count = await create_agent()

async def create_agent():
    mcp_tools = []
    try:
        client = create_mcp_client()
        mcp_tools = await asyncio.wait_for(client.get_tools(), timeout=5.0)
        print(f"✅ [MCP] 도구 로드 성공! ({len(mcp_tools)}개 도구)")
    except Exception as e:
        print(f"⚠️ [MCP] 도구 로드 실패 또는 건너뜀 (사유: {e})")

    all_tools = mcp_tools + [read_recent_emails, send_gmail]
    print(f"🛠️ 최종 탑재된 총 도구 개수: {len(all_tools)}")
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
    # Validate direct HTTP commands before running Gemini; preserve the user_input contract.
    user_input: str = Field(strict=True, min_length=1, max_length=20_000, pattern=r"\S")

# ----------------------------------------------------
# 목적: FastAPI lifespan 이벤트 처리 (on_event 대체)
# 이유: DeprecationWarning 해결 및 초기화 실패 방지
# 주의점: 백그라운드 태스크나 외부 연결 실패 시 서버 기동을 막지 않도록 예외 처리
# ----------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """서버 기동 시 백그라운드로 안전하게 에이전트 준비"""
    print("🔥 FastAPI 앱 초기화 시작...")
    try:
        generate_and_inject_jwt("jeaje")
        import asyncio
        asyncio.create_task(get_or_create_agent())
    except Exception as e:
        print(f"❌ 초기화 중 에러: {e}")

def require_agent_bearer(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Require a valid CommonAuth access token before exposing sensitive agent APIs."""
    # 목적: 에이전트와 Gmail 경로에서 인증을 먼저 강제해 익명 호출을 차단합니다.
    # 주의: 서명 키는 소스에 저장하지 않고 보호된 서비스 환경에서 읽습니다.
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid bearer token", headers={"WWW-Authenticate": "Bearer"})
    try:
        return CommonAuth().verify_token(token.strip(), expected_type="access")
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid bearer token", headers={"WWW-Authenticate": "Bearer"}) from None
    except RuntimeError:
        # 설정 오류는 인증 우회 대신 서비스 설정 오류로 닫힌 실패 처리합니다.
        raise HTTPException(status_code=503, detail="Authentication configuration unavailable") from None
    
@app.get("/gmail/read")
#async def api_read_recent_emails(max_results: int = Query(default=3)):
async def api_read_recent_emails(
    max_results: int = Query(default=3),
    # Gmail 데이터는 인증된 요청에만 공개합니다.
    _authenticated_claims: dict[str, Any] = Depends(require_agent_bearer),
):
    """최근 이메일 읽기 엔드포인트"""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, read_recent_emails.invoke, {"max_results": max_results})
        return {"result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gmail/send")
# async def api_send_gmail(req: MailSendRequest):
async def api_send_gmail(
    req: MailSendRequest,
    # 인증 실패 시 메일 발송 핸들러에 진입하지 않도록 합니다.
    _authenticated_claims: dict[str, Any] = Depends(require_agent_bearer),
):
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
async def api_chat_agent(
    req: ChatRequest,
    _authenticated_claims: dict[str, Any] = Depends(require_agent_bearer),
):
    """에이전트와의 대화 및 도구 사용 엔드포인트"""
    try:
        # 에이전트가 아직 없으면 즉시 생성
        current_agent = await get_or_create_agent()
        
        import asyncio
        thread_id = str(uuid4())
        result = await asyncio.wait_for(
            current_agent.ainvoke(
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

MCP_AUTH_SERVER_URL = "http://127.0.0.1:8000"

# 1. OpenID 및 OAuth 메타데이터 포워딩
@app.get("/.well-known/{path:path}")
async def proxy_well_known(path: str, request: FastAPIRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{MCP_AUTH_SERVER_URL}/.well-known/{path}", params=dict(request.query_params))
        return FastAPIResponse(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

# 2. OAuth 토큰 및 인증 포워딩
@app.api_route("/authorize", methods=["GET", "POST"])
@app.api_route("/token", methods=["POST"])
async def proxy_oauth(request: FastAPIRequest):
    async with httpx.AsyncClient() as client:
        body = await request.body()
        resp = await client.request(
            method=request.method,
            url=f"{MCP_AUTH_SERVER_URL}{request.url.path}",
            headers=dict(request.headers),
            content=body
        )
        return FastAPIResponse(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

# 3. MCP Messages 포워딩
@app.post("/messages")
async def proxy_messages(request: FastAPIRequest):
    async with httpx.AsyncClient() as client:
        body = await request.body()
        resp = await client.post(
            f"{MCP_AUTH_SERVER_URL}/messages", 
            headers=dict(request.headers), 
            content=body
        )
        return FastAPIResponse(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

# 4. MCP 통합 엔드포인트 포워딩 (/mcp)
@app.api_route("/mcp", methods=["GET", "POST"])
async def proxy_mcp(request: FastAPIRequest):
    async with httpx.AsyncClient() as client:
        body = await request.body()
        # resp = await client.request(
        #     method=request.method,
        #     url=f"{MCP_AUTH_SERVER_URL}/mcp",
        #     headers=dict(request.headers),
        #     content=body,
        #     timeout=60.0
        # )
        # proxy_mcp 함수에서:
        resp = await client.request(
            method=request.method,
            url=f"{MCP_AUTH_SERVER_URL}/mcp",
            headers=dict(request.headers), # <--- [원인!]
            content=body
        )
        return FastAPIResponse(
            content=resp.content, 
            status_code=resp.status_code, 
            media_type=resp.headers.get("content-type")
        )


# SSE 스트림 포워딩 추가
@app.get("/sse")
async def proxy_sse(request: FastAPIRequest):
    async with httpx.AsyncClient() as client:
        # 8000번의 실제 sse 엔드포인트로 전달 (필요시 /mcp 또는 /sse)
        req = client.build_request("GET", f"{MCP_AUTH_SERVER_URL}/sse", headers=dict(request.headers), timeout=None)
        resp = await client.send(req, stream=True)
        return FastAPIResponse(content=await resp.aread(), status_code=resp.status_code, media_type=resp.headers.get("content-type"))



if __name__ == "__main__":
    # uvicorn.run(app, host="0.0.0.0", port=8012)  <-- 이 부분을 주석 처리!
    asyncio.run(main()) # 순수 CLI 처리 로직만 남겨둠
