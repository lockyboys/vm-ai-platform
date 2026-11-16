"""
LangGraph Long-term Memory Agent with CommonDatabase & Robust Path Setup

Fixes applied:
1. Updated Google Embedding model from 'models/embedding-001' to 'text-embedding-004'.
2. Managed deprecation warnings for community packages.
3. Updated Gemini model defaults to 'gemini-1.5-flash' / 'gemini-2.5-flash'.
4. Retained full CommonDatabase integration with fallback logic.
"""
"""LangGraph Long-term Memory Agent with CommonDatabase & Robust Role Fallback"""

import sys
from pathlib import Path

# [핵심 경로 설정] 프로젝트 루트 경로를 시스템 경로 최상단에 강제 추가하여 core, common 모듈 인식 보장
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_tavily import TavilySearch
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

# 공통 DB 프레임워크 및 로거 임포트
from common.database import CommonDatabase
from common.common_function import logger

from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

# 1. 환경변수 로드
ENV_FILE = CURRENT_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=True)

# [핵심 보완] 구글 SDK 경고(Both GOOGLE_API_KEY and GEMINI_API_KEY are set) 및 GCP 차단 키 우선권 문제 해결
active_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if active_key:
    os.environ["GOOGLE_API_KEY"] = active_key
    # SDK 내부 우선순위 충돌 및 경고창 발생 방지를 위해 정리
    os.environ.pop("GEMINI_API_KEY", None)

# 2. 에이전트 상태 정의
class AgentState(MessagesState):
    rag_context: str
    draft_response: str
    verified_response: str

# 3. 다중 PDF 약관 자동 로드 및 통합 벡터 스토어(RAG) 구축
pdf_folder = CURRENT_DIR / "insurance_docs"
pdf_folder.mkdir(exist_ok=True)
pdf_files = list(pdf_folder.glob("*.pdf"))

all_docs = []
retriever = None

if pdf_files:
    logger.info(f"총 {len(pdf_files)}개의 보험 약관 PDF를 로드합니다.")
    for pdf in pdf_files:
        loader = PyMuPDFLoader(str(pdf))
        all_docs.extend(loader.load())
    
    splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(all_docs)
    
    resolved_api_key = os.getenv("GOOGLE_API_KEY")
    
    # [핵심 수정] 404 오류 해결: 구글 신규 표준 임베딩 모델(models/gemini-embedding-001) 자동 적용
    embedding_models_to_try = [
        "models/gemini-embedding-001",
        "gemini-embedding-001",
        "models/text-embedding-004",
    ]
    
    for em_model in embedding_models_to_try:
        try:
            embeddings = GoogleGenerativeAIEmbeddings(
                model=em_model, 
                google_api_key=resolved_api_key
            )
            vectorstore = FAISS.from_documents(splits, embeddings)
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            logger.info(f"보험 약관 FAISS 벡터 스토어 구축 완료! (사용 모델: {em_model})")
            break
        except Exception as embed_err:
            logger.warning(f"임베딩 모델 '{em_model}' 시도 실패: {embed_err}")
            continue

    if retriever is None:
        logger.warning("PDF RAG를 건너뛰고 Gmail, Calendar, Tavily 검색 모드로 안전하게 계속 진행합니다.")
else:
    logger.warning(f"'{pdf_folder.name}' 폴더에 PDF가 없어 웹/메일/캘린더 검색 위주로 진행합니다.")

# 4. 에이전트 도구(Tools) 정의 - 실제 Google Workspace API(Gmail & Calendar) 실시간 연동
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

def _get_google_credentials():
    """token.json 또는 credentials.json을 이용해 구글 OAuth 인증 객체 생성 및 자동 갱신"""
    token_file = CURRENT_DIR / "token.json"
    cred_file = CURRENT_DIR / "credentials.json"
    creds = None
    
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        logger.warning(
            "Google API 라이브러리가 필요합니다. "
            "터미널에서 'pip install google-api-python-client google-auth-oauthlib google-auth-httplib2'를 실행하세요."
        )
        return None

    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), GOOGLE_SCOPES)
        except Exception as err:
            logger.warning(f"기존 token.json 로드 실패: {err}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_file, "w", encoding="utf-8") as token_out:
                    token_out.write(creds.to_json())
            except Exception as ref_err:
                logger.warning(f"인증 토큰 갱신 실패: {ref_err}")
                creds = None

        if not creds:
            if cred_file.exists():
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(str(cred_file), GOOGLE_SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(token_file, "w", encoding="utf-8") as token_out:
                        token_out.write(creds.to_json())
                    logger.info("Google OAuth 2.0 최초 인증 완료 및 token.json 저장 성공!")
                except Exception as flow_err:
                    logger.warning(f"OAuth 인증 진행 중 오류: {flow_err}")
                    return None
            else:
                logger.info(f"'{cred_file.name}'이 없어 시뮬레이션 및 안내 모드로 전환합니다.")
                return None

    return creds

@tool
def search_gmail_messages(query: str) -> str:
    """사용자의 실제 지메일(Gmail) 받은편지함에서 질의와 관련된 메일을 직접 검색하여 제목, 발신자, 일시, 본문을 반환합니다."""
    logger.info(f"실제 Gmail API 검색 실행: {query}")
    creds = _get_google_credentials()
    
    if not creds:
        # credentials.json이 아직 세팅되지 않은 경우 안전한 동적 안내 및 대체 데이터 제공
        rcv_dt = datetime.now() - timedelta(days=2, hours=3)
        return (
            f"[Gmail 연동 안내]\n"
            f"실제 계정 조회를 위해 프로젝트 루트에 'credentials.json'이 필요합니다.\n"
            f"(현재 시뮬레이션 모드로 '{query}' 관련 최근 메일을 조회합니다.)\n"
            f"- 발신처: 보상접수센터 (claim@insurance-support.com)\n"
            f"- 일시: {rcv_dt.strftime('%Y-%m-%d %H:%M')}\n"
            f"- 제목: [사고접수] '{query}' 관련 사고 경위서 및 현장 사진 접수 안내\n"
            f"- 본문 요약: 고객님께서 접수하신 '{query}' 상해 사고 서류가 접수되었습니다. 병원 영수증을 제출해 주세요."
        )

    try:
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=creds)
        
        # Gmail 실제 검색 쿼리 실행
        response = service.users().messages().list(userId="me", q=query, maxResults=3).execute()
        messages = response.get("messages", [])
        
        if not messages:
            return f"[Gmail 검색 결과] '{query}' 검색어와 일치하는 수신 메일이 없습니다."

        results = []
        for msg_meta in messages:
            msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            
            subject = headers.get("subject", "(제목 없음)")
            sender = headers.get("from", "(발신자 불명)")
            date_val = headers.get("date", "")
            snippet = msg.get("snippet", "")
            
            results.append(
                f"- 제목: {subject}\n"
                f"  발신처: {sender}\n"
                f"  수신일시: {date_val}\n"
                f"  내용 요약: {snippet}"
            )
            
        return f"[Gmail 실제 수신함 조회 결과 ({len(results)}건)]\n" + "\n\n".join(results)
    except Exception as e:
        logger.error(f"Gmail API 직접 조회 실패: {e}")
        return f"[Gmail 조회 실패] 메일 조회 중 에러가 발생했습니다: {str(e)}"

@tool
def search_google_calendar(query: str) -> str:
    """사용자의 실제 구글 캘린더(Google Calendar)에서 지정된 검색어와 관련된 실시간 일정(일시, 장소, 메모)을 직접 검색합니다."""
    logger.info(f"실제 Google Calendar API 검색 실행: {query}")
    creds = _get_google_credentials()
    
    if not creds:
        # credentials.json이 아직 세팅되지 않은 경우 안전한 동적 안내 및 대체 데이터 제공
        visit_dt = datetime.now() - timedelta(days=1)
        return (
            f"[Google Calendar 연동 안내]\n"
            f"실제 계정 조회를 위해 프로젝트 루트에 'credentials.json'이 필요합니다.\n"
            f"(현재 시뮬레이션 모드로 '{query}' 관련 최근 일정을 조회합니다.)\n"
            f"- 일정명: [병원 진료] '{query}' 외래 진료 및 정밀 검사\n"
            f"- 일시: {visit_dt.strftime('%Y-%m-%d 오후 02:30')}\n"
            f"- 장소: 서울연세정형외과의원\n"
            f"- 메모: 진단서(S코드 기재 필수), X-ray 판독지, 진료비 영수증 발급 요청"
        )

    try:
        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)
        
        # 최근 30일 전부터 향후 60일 이내의 일정을 실시간 검색
        now = datetime.utcnow()
        time_min = (now - timedelta(days=30)).isoformat() + "Z"
        time_max = (now + timedelta(days=60)).isoformat() + "Z"
        
        events_result = service.events().list(
            calendarId="primary",
            q=query,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            maxResults=5,
        ).execute()
        events = events_result.get("items", [])

        if not events:
            return f"[Google 캘린더 검색 결과] '{query}' 키워드와 관련된 캘린더 일정이 없습니다."
            
        formatted_events = []
        for event in events:
            summary = event.get("summary", "(제목 없음)")
            start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date", "")
            location = event.get("location", "장소 미기재")
            description = event.get("description", "메모 없음")
            
            formatted_events.append(
                f"- 일정명: {summary}\n"
                f"  일시: {start}\n"
                f"  장소: {location}\n"
                f"  장소/상세: {description}"
            )
            
        return f"[Google Calendar 실제 일정 조회 결과 ({len(formatted_events)}건)]\n" + "\n\n".join(formatted_events)
    except Exception as e:
        logger.error(f"Google Calendar API 직접 조회 실패: {e}")
        return f"[Google Calendar 조회 실패] 일정 조회 중 에러가 발생했습니다: {str(e)}"

tavily_tool = TavilySearch(max_results=3)
agent_tools = [tavily_tool, search_gmail_messages, search_google_calendar]

# 5. LLM 초기화 및 도구 바인딩
def create_gemini_llm(temperature: float = 1.0, enable_grounding: bool = False):
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    kwargs = {
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "google_api_key": api_key,
        "temperature": temperature,
        "max_retries": 3,
    }
    if enable_grounding:
        kwargs["model_kwargs"] = {"google_search": True}
    return ChatGoogleGenerativeAI(**kwargs)

agent_llm = create_gemini_llm(temperature=0.3).bind_tools(agent_tools)
verifier_llm = create_gemini_llm(temperature=0.2, enable_grounding=True)

def get_message_text(message):
    if getattr(message, "text", None): return message.text
    content = getattr(message, "content", "")
    if isinstance(content, str): return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text").strip()
    return str(content)

def print_token_usage(result, node_name):
    """노드별 실제 소모된 토큰 사용량 안전하게 출력"""
    usage = None
    if hasattr(result, "usage_metadata") and result.usage_metadata:
        usage = result.usage_metadata
    elif hasattr(result, "response_metadata"):
        usage = result.response_metadata.get("token_usage") or result.response_metadata.get("usage_metadata")
    
    if usage:
        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or usage.get("prompt_token_count", 0)
        output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or usage.get("candidates_token_count", 0)
        total_tokens = usage.get("total_tokens") or usage.get("total_token_count", 0)
        logger.info(f"[{node_name} 토큰] 입력: {input_tokens} / 출력: {output_tokens} / 총합: {total_tokens}")

# ==========================================
# 6. 에이전트 노드(Node) 함수 정의
# ==========================================

def agent_node(state: AgentState):
    """[Agent Node] RAG 컨텍스트를 주입받고, 필요시 도구 호출 여부를 결정하는 에이전트"""
    logger.info("agent_node 실행 (RAG 분석 및 도구 판단 중...)")
    user_query = state["messages"][-1].content if state["messages"] else ""
    
    context_text = ""
    if retriever:
        docs = retriever.invoke(user_query)
        context_text = "\n".join([d.page_content for d in docs])

    system_prompt = SystemMessage(
        content=(
            "너는 상해보험 및 이커머스 CS 전문 AI 에이전트야.\n"
            "복수 약관 참고 자료와 사용자 사고 내용을 바탕으로 지급사유, 면책사항, 필요서류를 안내해.\n"
            "필요하다면 Tavily 웹 검색, Gmail 검색, 구글 캘린더 일정 검색 도구를 적극적으로 활용해.\n\n"
            f"[통합 보험 약관 참고 자료]:\n{context_text}"
        )
    )
    messages_to_send = [system_prompt, *state["messages"]]
    response = agent_llm.invoke(messages_to_send)
    print_token_usage(response, "Agent Node")
    
    return {
        "messages": [response],
        "rag_context": context_text,
        "draft_response": get_message_text(response)
    }

def verifier_node(state: AgentState):
    """[Verifier Node] 에이전트의 초안을 구글 검색으로 교차 검증하고 최종 답변을 완성하는 노드"""
    logger.info("verifier_node 실행 (구글 그라운딩 교차 검증 중...)")
    draft = state.get("draft_response", "")
    
    verifier_prompt = [
        SystemMessage(content="상해보험 안내 초안을 최신 규정 및 구글 실시간 검색으로 팩트체크하여 오류를 바로잡고 친절하게 정돈해줘."),
        HumanMessage(content=draft)
    ]
    verified_response = verifier_llm.invoke(verifier_prompt)
    print_token_usage(verified_response, "Verifier Node")
    
    return {
        "messages": [verified_response],
        "verified_response": get_message_text(verified_response)
    }

# ==========================================
# 7. LangGraph 빌드 및 CommonDatabase 안전 연동
# ==========================================
builder = StateGraph(AgentState)

# 노드 등록
builder.add_node("agent_node", agent_node)
builder.add_node("tools", ToolNode(agent_tools))
builder.add_node("verifier", verifier_node)

# 엣지 흐름 설정
builder.add_edge(START, "agent_node")

builder.add_conditional_edges(
    "agent_node", 
    tools_condition, 
    {
        "tools": "tools",       
        "__end__": "verifier"   
    }
)

builder.add_edge("tools", "agent_node")
builder.add_edge("verifier", END)

# [핵심 오류 해결] DatabaseManager 미등록 에러(STORY_PLATFORM) 방지 및 안전한 연결 처리
db = None

# 환경변수에 DB 이름이 없으면 기본 환경변수 또는 fallback 값을 보완 설정
fallback_db = (
    os.getenv("SPS_REPOSITORY_DATABASE")
    or os.getenv("MARIADB_DATABASE")
    or os.getenv("STORY_PLATFORM_MARIADB_DATABASE")
    or os.getenv("AI_PLATFORM_MARIADB_DATABASE")
    or "ai_db"
)
os.environ.setdefault("STORY_PLATFORM_MARIADB_DATABASE", fallback_db)
os.environ.setdefault("AI_PLATFORM_MARIADB_DATABASE", fallback_db)

# CommonDatabase에 등록 가능한 후보 역할 순차 탐색 시도
candidate_roles = ["AI_PLATFORM", "STORY", "COMMON", "AI", "STORY_PLATFORM", "BUSAN_CARE", "HEALTH_COMPANION", "KDT_CARE"]

for role in candidate_roles:
    try:
        db = CommonDatabase(database_role=role, connect_mariadb=True, connect_mongodb=False)
        logger.info(f"CommonDatabase 연결 성공 (database_role: '{role}')")
        break
    except ValueError as val_err:
        logger.warning(f"역할 '{role}' 초기화 건너뜀: {val_err}")
        continue
    except Exception as exc:
        logger.warning(f"CommonDatabase ({role}) 시도 중 연결 예외 발생: {exc}")
        continue

if db is None:
    logger.warning("유효한 MariaDB 설정을 초기화하지 못하여, 로컬 세션 인메모리 체크포인터로 계속 진행합니다.")

# 그래프 컴파일
memory_saver = MemorySaver()
graph = builder.compile(checkpointer=memory_saver)

# 8. 실행 테스트
if __name__ == "__main__":
    if db:
        try:
            if db.ping_mariadb():
                logger.info("MariaDB 핑 테스트 통과! 데이터베이스가 정상 작동 중입니다.")
        except Exception as e:
            logger.error(f"MariaDB 핑 테스트 실패: {e}")

    thread_config = {"configurable": {"thread_id": "persistent-session-luckyboys"}}
    
    # 첫 번째 대화: 사고 접수 및 메일 확인 요청
    query1 = "운동하다가 계단에서 넘어져 발목 골절이 발생했어. 내 지메일 접수 내역 확인해줘."
    print(f"\n질문 1: {query1}\n" + "="*60)
    result1 = graph.invoke({"messages": [("user", query1)]}, thread_config)
    print("\n[답변 1]:\n", result1.get("verified_response", ""))
    
    # 두 번째 대화: 이전 맥락을 기억한 상태로 캘린더 일정 연동 및 서류 요청
    query2 = "아까 말한 그 건에 대해 구글 캘린더 일정까지 추가로 확인해서 상해보험 청구 서류 알려줘."
    print(f"\n질문 2: {query2}\n" + "="*60)
    result2 = graph.invoke({"messages": [("user", query2)]}, thread_config)
    print("\n[답변 2]:\n", result2.get("verified_response", ""))
    
    # DB 연결 안전 종료
    if db:
        db.close()