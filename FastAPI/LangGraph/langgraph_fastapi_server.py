"""Gemini + Tavily + LangGraph 비동기 FastAPI 에이전트 서버."""
# 통합 설치     pip install langchain langchain-core langchain-google-genai langgraph langchain-tavily fastapi uvicorn python-dotenv google-genai	에이전트와 FastAPI 서버 구동에 필요한 모든 라이브러리를 설치합니다.
# 가상환경 확인 python -m pip install --upgrade pip     패키지 충돌 방지를 위해 pip 버전을 최신으로 업데이트합니다.
# cd /data/vm_project/FastAPI/LangGraph
# python -m uvicorn main:app --host 0.0.0.0 --port 8001
# curl -X 'POST' \ 'POST' \
#   'http://localhost:8001/api/chat' \
#   -H 'accept: application/json' \
#   -H 'Content-Type: application/json' \
#   -d '{
#   "query": "과천정부청사역에서 출발하는 2026년 서울 최신 여행지 추천해줘",
#   "thread_id": "user-luckyboys-01"
# }'
# 관리 명령어:
# sudo systemctl status fastapi-langgraph.service --no-pager
# sudo systemctl restart fastapi-langgraph.service
# sudo journalctl -u fastapi-langgraph.service -f
import os
import asyncio
from datetime import date
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

# 환경변수 로드
# 기존의 고정된 윈도우 경로 대신 아래 코드로 변경하세요
CURRENT_DIR = Path(__file__).resolve().parent
CURRENT_DATE = date.today().isoformat()

# 1. 현재 디렉토리 또는 상위 디렉토리에서 .env 파일 탐색
ENV_FILE = None
for parent in [CURRENT_DIR, *CURRENT_DIR.parents]:
    potential_env = parent / ".env"
    if potential_env.exists():
        ENV_FILE = potential_env
        break

# 만약 못 찾았을 경우 기본값 지정 또는 예외 처리
if not ENV_FILE or not ENV_FILE.exists():
    # 서버 환경 내 실제 .env 파일 위치가 있다면 직접 지정할 수도 있습니다.
    ENV_FILE = CURRENT_DIR / ".env" 

if not ENV_FILE.exists():
    raise FileNotFoundError(f".env 파일을 찾을 수 없습니다. 경로를 확인해주세요: {ENV_FILE}")

load_dotenv(dotenv_path=ENV_FILE, override=True)

# 1. FastAPI 앱 및 Pydantic 모델 설정
app = FastAPI(title="AI Agent API", description="여행 추천 및 팩트체크 에이전트", version="1.0")

class ChatRequest(BaseModel):
    query: str
    thread_id: str = "default-thread"

class SimpleState(MessagesState):
    draft_response: str
    verified_response: str

# 2. LLM 및 도구 초기화
def create_gemini_llm(temperature: float = 1.0, enable_grounding: bool = False):
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("API 키가 설정되지 않았습니다.")
    
    kwargs = {
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "google_api_key": api_key,
        "temperature": temperature,
        "max_retries": 3,
    }
    
    # model_kwargs를 통한 설정 전달 (경고 회피용)
    if enable_grounding:
        kwargs["model_kwargs"] = {"google_search": True}

    return ChatGoogleGenerativeAI(**kwargs)

tavily_tool = TavilySearch(max_results=3)
llm_tavily = create_gemini_llm().bind_tools([tavily_tool])
llm_google_verifier = create_gemini_llm(temperature=0.2, enable_grounding=True)

def get_message_text(message):
    if getattr(message, "text", None): return message.text
    content = getattr(message, "content", "")
    if isinstance(content, str): return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text").strip()
    return str(content)

# 3. 비동기 노드(Node) 정의
async def chatbot(state: SimpleState):
    """1단계: 비동기 Tavily 검색 및 초안 작성"""
    system_message = SystemMessage(
        content=(
            "너는 여행 추천 가이드야.\n"
            "사용자의 조건을 고려하여 실제 서울 여행장소 8곳을 추천해.\n"
            "최신 여행 정보 및 교통편이 필요하면 Tavily 검색 도구를 사용해.\n"
            f"모든 최신성 판단은 기준일 {CURRENT_DATE} 현재 자료를 기준으로 해.\n"
            "검색 결과로 확인되지 않은 사실은 지어내지 마."
        )
    )
    messages_to_send = [system_message, *state["messages"]]
    
    # 비동기 LLM 호출 (ainvoke)
    result = await llm_tavily.ainvoke(messages_to_send)
    
    return {
        "messages": [result],
        "draft_response": get_message_text(result),
    }

async def google_verifier(state: SimpleState):
    """2단계: 비동기 구글 Grounding 교차 검증"""
    draft = state.get("draft_response", "")
    verifier_prompt = [
        SystemMessage(
            content=(
                "너는 엄격한 팩트체커야. 1단계 초안과 구글 실시간 검색 결과를 비교하여 검증해.\n"
                f"검증 기준일은 {CURRENT_DATE}이며, 사용자가 요청한 연도와 관계없이 기준일 현재 자료를 우선해.\n"
                "정보 불일치 시 최신 구글 검색 결과를 우선 반영하고, 차이점을 명시해줘.\n"
                "최종 추천안을 깔끔하게 정리해."
            )
        ),
        HumanMessage(content=f"다음 초안을 구글 검색으로 교차 검증해줘:\n\n{draft}"),
    ]

    try:
        # 비동기 LLM 호출 (ainvoke)
        verified_result = await llm_google_verifier.ainvoke(verifier_prompt)
        final_text = get_message_text(verified_result)
    except Exception as e:
        print(f"[경고] 구글 검증 실패, 초안 유지: {e}")
        final_text = draft

    return {
        "messages": [verified_result] if 'verified_result' in locals() else state["messages"],
        "verified_response": final_text,
    }

# 4. LangGraph 그래프 빌드
def build_graph():
    builder = StateGraph(SimpleState)
    builder.add_node("chatbot", chatbot)
    builder.add_node("tools", ToolNode([tavily_tool]))
    builder.add_node("verifier", google_verifier)

    builder.add_edge(START, "chatbot")
    builder.add_conditional_edges("chatbot", tools_condition, {"tools": "tools", "__end__": "verifier"})
    builder.add_edge("tools", "chatbot")
    builder.add_edge("verifier", END)
    
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)

agent_graph = build_graph()

# 5. FastAPI 엔드포인트 라우터
@app.get("/", response_class=HTMLResponse)
async def web_chat() -> HTMLResponse:
    """브라우저에서 사용하는 간단한 에이전트 채팅 화면."""
    return HTMLResponse("""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 여행 팩트체크 에이전트</title>
<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;background:#f6f7fb;color:#202124}h1{margin-bottom:8px}.box{background:#fff;border-radius:16px;padding:20px;box-shadow:0 4px 20px #0001}textarea{width:100%;min-height:110px;padding:12px;border:1px solid #ccd1d9;border-radius:10px;font-size:16px;box-sizing:border-box}button{margin-top:12px;padding:11px 20px;border:0;border-radius:8px;background:#2563eb;color:#fff;font-size:16px;cursor:pointer}button:disabled{background:#9ca3af}pre{white-space:pre-wrap;background:#f1f3f5;padding:16px;border-radius:10px;min-height:100px}</style></head>
<body><h1>AI 여행 팩트체크 에이전트</h1><p>Gemini + Tavily + LangGraph</p><div class="box"><textarea id="query" placeholder="질문을 입력하세요. 예: 과천에서 출발하는 2026년 서울 여행지 추천"></textarea><br><button id="send">질문 보내기</button><h3>응답</h3><pre id="answer">아직 응답이 없습니다.</pre></div>
<script>const q=document.getElementById('query'),b=document.getElementById('send'),a=document.getElementById('answer');b.onclick=async()=>{if(!q.value.trim())return;a.textContent='검색 및 검증 중입니다...';b.disabled=true;try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q.value,thread_id:'web-'+Date.now()})});const d=await r.json();a.textContent=d.response||d.detail||'응답이 없습니다.';}catch(e){a.textContent='오류: '+e.message;}finally{b.disabled=false;}};</script></body></html>""")

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """비동기 방식으로 에이전트를 실행하고 응답을 반환합니다."""
    thread_config = {"configurable": {"thread_id": req.thread_id}}
    
    try:
        # 그래프를 비동기로 실행 (ainvoke)
        result = await agent_graph.ainvoke(
            {"messages": [("user", req.query)]},
            thread_config
        )
        
        final_response = result.get("verified_response", "")
        if not final_response:
            final_response = get_message_text(result["messages"][-1])
            
        return {
            "status": "success",
            "thread_id": req.thread_id,
            "response": final_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # uvicorn을 사용해 비동기 서버 실행
    uvicorn.run(app, host="0.0.0.0", port=8002)
