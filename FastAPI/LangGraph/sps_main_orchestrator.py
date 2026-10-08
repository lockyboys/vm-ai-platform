# 4. 메인 컨트롤 타워 (sps_main_orchestrator.py)
# 무거운 비즈니스 로직은 위 3개의 에이전트 파일로 모두 넘기고, API 라우팅(FastAPI)과 MCP 챗 연결(LangGraph)만 담당하는 
# 날렵한 메인 서버입니다.
#
# Plaintext
# /data/vm_project/FastAPI/LangGraph/
#  ├── config.py                      # [신규] 루트 공통 설정 (API Key 등)
#  ├── common/                        # [신규] 공통 모듈 폴더
#  │    ├── database.py               # (향후 MariaDB/VectorDB 공통 연결용)
#  │    └── common_function.py        # (공통 유틸리티)
#  │
#  ├── haness/                        # [이동] SPS haness MCP 메인 소스 폴더
#  │    ├── sps_main_orchestrator.py  # 메인 서버 (haness 내부로 이동)
#  │    ├── Agent_Import_RAGs/        # RAG 에이전트
#  │    │    └── LangGraph_Ingestion_Pipeline.py
#  │    └── Agent_Import_PFDs/        # 자율 탐색 및 Vision 에이전트
#  │         ├── LangGraph_API_Extractor.py
#  │         └── LangGraph_Network_Sniffer.py
#  │
#  └── insurance_docs/                # PDF 저장소
# 
# curl -X POST http://127.0.0.1:8000/api/crawler/run \
#   -H "Content-Type: application/json" \
#   -d '{"target_url": "https://www.axa.co.kr/AsianPlatformInternet/html/Axa.html"}'
# Windows CMD / PowerShell 환경일 경우
# curl -X POST http://127.0.0.1:8000/api/crawler/run ^
#   -H "Content-Type: application/json" ^
#   -d "{\"target_url\": \"https://www.axa.co.kr/AsianPlatformInternet/html/Axa.html\"}"
# FastAPI/LangGraph/sps_main_orchestrator.py
import sys
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# [핵심 수정] 루트 폴더(/data/vm_project)를 경로에 추가하여 기존 config.py를 로드합니다.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import config  # 루트에 있는 config.py 적용 (4번 지침 준수)

# 기존 에이전트 폴더 모듈 임포트 유지 (haness 폴더 래핑 취소)
from Agent_Import_RAGs.LangGraph_Ingestion_Pipeline import build_vector_db, query_insurance_rag
from Agent_Import_PFDs.LangGraph_Network_Sniffer import explore_unknown_site

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

app = FastAPI(title="SPS haness MCP Orchestrator")

# --- 데이터 모델 ---
class ChatRequest(BaseModel):
    query: str

# --- 자연어 도구(Tool) ---
@tool
async def run_crawler_tool(company_name: str, target_url: str = "") -> str:
    """보험사의 약관 PDF를 크롤링하고 다운로드할 때 호출하는 자율 탐색 도구입니다."""
    if not target_url:
        if "AXA" in company_name.upper() or "악사" in company_name:
            target_url = "https://www.axa.co.kr/AsianPlatformInternet/html/Axa.html"
    print(f"🛠️ [Tool 실행] {company_name} 크롤러 가동 (URL: {target_url})")
    selector = await explore_unknown_site(target_url)
    return f"[{company_name}] {selector}"

# --- LangGraph 빌더 ---
def create_agent_graph():
    tools = [run_crawler_tool]
    tool_node = ToolNode(tools)
    
    # config.py의 설정을 사용(Langchain은 내부적으로 os.environ도 확인하지만 명시적 관리를 위해 공통 룰 적용)
    model = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0)
    model_with_tools = model.bind_tools(tools)

    async def agent_node(state: MessagesState): 
        return {"messages": [await model_with_tools.ainvoke(state["messages"])]}

    def should_continue(state: MessagesState):
        if state["messages"][-1].tool_calls: return "tools"
        return "verifier"

    async def verifier_node(state: MessagesState):
        prompt = "도구 호출 결과를 친절히 요약 보고해. 지어내기 금지."
        return {"messages": [await model.ainvoke([*state["messages"], HumanMessage(content=prompt)])]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_node("verifier", verifier_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, ["tools", "verifier"])
    builder.add_edge("tools", "agent")
    builder.add_edge("verifier", END)
    return builder.compile()

sps_graph = create_agent_graph()

@app.post("/api/gemini/chat")
async def api_chat_orchestrator(req: ChatRequest):
    try:
        state = await sps_graph.ainvoke({"messages": [HumanMessage(content=req.query)]})
        return {"success": True, "response": state["messages"][-1].content}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # 실행 시 경로는 리눅스 기준에 맞춥니다.
    print("🚀 SPS haness MCP 구동 완료 - http://0.0.0.0:8080")
    uvicorn.run("sps_main_orchestrator:app", host="0.0.0.0", port=8080, reload=True)