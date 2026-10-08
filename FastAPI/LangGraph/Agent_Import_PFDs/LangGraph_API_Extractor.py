# Agent_Import_PFDs/LangGraph_API_Extractor.py
# LangGraph_API_Extractor.py
# 1. 시각 분석 에이전트 (LangGraph_API_Extractor.py)
# Gemini Vision을 이용해 화면 구조를 분석하는 역할만 전담합니다.
# FastAPI/LangGraph/Agent_Import_PFDs/LangGraph_API_Extractor.py
import base64
from typing import Annotated
from typing_extensions import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

class ExtractorState(TypedDict):
    messages: Annotated[list, add_messages]
    base64_image: str

async def analyze_ui_with_vision(base64_image: str) -> str:
    """도메인에 국한되지 않고 화면 내 목표(버튼, 링크 등)를 찾아내는 범용 시각 에이전트입니다."""
    
    @tool
    def return_selector(selector: str, confidence: int, reason: str) -> str:
        """추출한 요소의 CSS/Text 선택자와 본인의 확신도(0~100)를 반환합니다."""
        if confidence < 80:
            return f"[자가 검증 실패] 확신도가 {confidence}로 낮습니다. 팝업, 가려짐 등을 고려해 다른 요소를 다시 분석하세요."
        return f"SUCCESS:{selector}"

    tools = [return_selector]
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0).bind_tools(tools)
    
    # [수정됨] 보험사 관련 하드코딩 제거, 범용 웹 탐색 에이전트로 프롬프트 변경
    sys_msg = SystemMessage(content="""당신은 웹 화면에서 사용자가 원하는 목표(예: 다운로드, 특정 메뉴, 공지사항 등)를 찾아내는 시각 분석 에이전트입니다.
    스스로 판단하여 가장 정확한 타겟을 찾으면 return_selector 도구를 호출하세요.
    직전 결과가 실패라면 기존 시각을 버리고 화면 가장자리, 팝업 닫기 버튼 등을 새롭게 타겟팅하세요.""")

    async def agent_node(state: ExtractorState):
        msgs = [sys_msg] + state["messages"]
        if not any(isinstance(m, HumanMessage) and isinstance(m.content, list) for m in msgs):
            msgs.append(HumanMessage(content=[
                {"type": "text", "text": "현재 웹 화면을 분석하여 클릭할 최적의 타겟을 찾고 도구를 호출하세요."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{state['base64_image']}"}}
            ]))
        return {"messages": [await llm.ainvoke(msgs)]}

    def should_continue(state: ExtractorState):
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return "tools"
        return END

    builder = StateGraph(ExtractorState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    
    graph = builder.compile()
    final_state = await graph.ainvoke({"messages": [], "base64_image": base64_image})
    
    for msg in reversed(final_state["messages"]):
        if msg.type == "tool" and msg.content.startswith("SUCCESS:"):
            return msg.content.replace("SUCCESS:", "")
            
    return "분석 실패: 에이전트가 스스로 판단한 결과 적절한 대상을 찾지 못했습니다."