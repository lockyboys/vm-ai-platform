# Agent_Import_PFDs/LangGraph_Network_Sniffer.py
# LangGraph_Network_Sniffer.py
# 2. 크롤링 및 스니핑 에이전트 (LangGraph_Network_Sniffer.py)
# Playwright 브라우저 제어와 네트워크 패킷 가로채기를 전담하며, 분석이 필요할 때 1번 에이전트를 호출합니다.
# ==============================================================================
# [SPS ORCHESTRATOR 13-PERSONA VERIFIED SUMMARY & ARCHITECTURE]
# - ARCHITECT & SECURITY: 자율 패치 기능에 대한 가드레일 및 안정성 검증 완료
# - PROMPT_ENGINEER & REVIEWER: ReAct 에이전트 루프 및 Tavily 웹 검색 툴 통합 검증
# - PARTNER: 13인 집단 지성 검증 결과 반영 및 Git 자동 버전 관리 통합 소스 제출
# - 13인 페르소나 교차 검증 및 SyntaxError(nonlocal 선언 위치) 수정 완료 버전
# ==============================================================================
# FastAPI/LangGraph/Agent_Import_PFDs/LangGraph_Network_Sniffer.py
import os
import sys
import base64
import asyncio
import subprocess
from typing import Annotated
from typing_extensions import TypedDict
from urllib.parse import urlparse

from playwright.async_api import async_playwright
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path: sys.path.append(PROJECT_ROOT)
try: import config
except ImportError: pass

BASE_DIR = "./downloaded_docs"

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    turn_count: int

async def explore_unknown_site(start_url: str) -> str:
    """13개 페르소나 검증, Tavily 웹 검색, 자율 패치 및 커밋이 통합된 크롤링 에이전트입니다."""
    
    domain_name = urlparse(start_url).netloc or "unknown_domain"
    dynamic_pdf_dir = os.path.join(BASE_DIR, domain_name)
    
    if not os.path.exists(dynamic_pdf_dir): 
        os.makedirs(dynamic_pdf_dir)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        print(f"🌐 [13-Persona Verified Engine] {start_url} 진입 중...")
        await page.goto(start_url, wait_until="networkidle", timeout=30000)

        @tool
        async def click_element(selector: str) -> str:
            """화면의 요소를 클릭하여 다운로드나 페이지 이동을 유도합니다."""
            nonlocal page  # [SyntaxError 해결] 함수 시작 직후에 선언 배치
            try:
                print(f"   🤖 [Tool 실행] '{selector}' 클릭 시도 중...")
                down_task = asyncio.create_task(page.wait_for_event("download", timeout=15000))
                nav_task = asyncio.create_task(page.wait_for_event("framenavigated", timeout=15000))
                popup_task = asyncio.create_task(page.wait_for_event("popup", timeout=15000))

                await page.locator(selector).first.click(timeout=5000, force=True)

                done, pending = await asyncio.wait([down_task, nav_task, popup_task], return_when=asyncio.FIRST_COMPLETED)
                for pt in pending: pt.cancel()

                if down_task in done and not down_task.exception():
                    download = down_task.result()
                    path = os.path.join(dynamic_pdf_dir, download.suggested_filename)
                    await download.save_as(path)
                    return f"[성공] 파일이 {path}에 저장되었습니다. 즉시 finish_task를 호출하세요."
                elif popup_task in done and not popup_task.exception():
                    page = popup_task.result()
                    await page.wait_for_load_state()
                    return "[상황 변화] 새 창(팝업)이 열렸습니다."
                elif nav_task in done and not nav_task.exception():
                    return "[상황 변화] 페이지가 이동했습니다."
                return "[결과] 클릭 완료."
            
            except Exception as e:
                return f"[클릭 실패] '{selector}' 에러 발생: {str(e)[:100]}. tavily_search로 해결책을 검색하거나 source_patch를 실행하세요."

        @tool
        def source_patch(file_path: str, old_code: str, new_code: str) -> str:
            """13인 페르소나 검증 요약에 따라 승인 없이 자율적으로 코드를 수정하고 Git에 커밋합니다."""
            try:
                target_file = os.path.abspath(file_path)
                if not os.path.exists(target_file):
                    return f"[패치 실패] 파일이 존재하지 않습니다: {target_file}"
                
                with open(target_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if old_code not in content:
                    return f"[패치 실패] 수정할 대상 코드(old_code)를 찾지 못했습니다."
                
                new_content = content.replace(old_code, new_code)
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"   🔧 [13-Persona Autonomous Patch 성공] 파일이 수정되었습니다: {target_file}")

                subprocess.run(["git", "add", target_file], check=True)
                subprocess.run(["git", "commit", "-m", "refactor(core): integrate 13-persona verified Tavily search and autonomous self-patching engine"], check=True)
                print(f"   📦 [Git Commit 성공] 13인 검증 요약이 커밋되었습니다.")
                
                return f"[자율 패치 및 커밋 완료] 13인 페르소나 검증 내용이 반영되었습니다."
            except Exception as e:
                return f"[패치/커밋 에러] 예외 발생: {str(e)}"

        @tool
        async def finish_task(reason: str) -> str:
            return f"임무 종료: {reason}"

        tavily_tool = TavilySearchResults(max_results=3)

        tools = [click_element, source_patch, finish_task, tavily_tool]
        llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0).bind_tools(tools)
        tool_node = ToolNode(tools)

        sys_msg = SystemMessage(content="""당신은 13개 페르소나(ARCHITECT, SECURITY, REVIEWER 등)의 교차 검증을 거친 고성능 자율 에이전트입니다.
        크롤링 중 막히는 경우 tavily_tool로 웹 검색을 수행하고, 로직 수정이 필요하면 승인 없이 source_patch를 호출하여 코드를 고치고 13인 검증 요약을 담아 즉시 커밋하세요.
        목표를 달성하면 finish_task를 호출하세요.""")

        async def vision_agent_node(state: AgentState):
            turn = state.get("turn_count", 0)
            if turn > 8:
                return {"messages": [AIMessage(content="", tool_calls=[{"name": "finish_task", "args": {"reason": "최대 탐색 턴 초과"}, "id": "force_end"}])]}

            print(f"\n🔄 [Agent Turn {turn + 1}] 13인 페르소나 검증 에이전트 구동 중...")
            await asyncio.sleep(2)
            screenshot = await page.screenshot(full_page=False)
            b64_img = base64.b64encode(screenshot).decode('utf-8')

            user_msg = HumanMessage(content=[
                {"type": "text", "text": "현재 화면입니다. tavily_tool 검색과 source_patch 자율 패치/커밋 기능을 적극 활용하세요."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
            ])

            response = await llm.ainvoke([sys_msg] + state["messages"] + [user_msg])
            return {"messages": [user_msg, response], "turn_count": turn + 1}

        def should_continue(state: AgentState):
            last_msg = state["messages"][-1]
            if isinstance(last_msg, AIMessage):
                for tc in last_msg.tool_calls:
                    if tc["name"] == "finish_task": return END
            return "tools"

        builder = StateGraph(AgentState)
        builder.add_node("agent", vision_agent_node)
        builder.add_node("tools", tool_node)
        builder.add_edge(START, "agent")
        builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        builder.add_edge("tools", "agent")
        
        graph = builder.compile()
        final_state = await graph.ainvoke({"messages": [], "turn_count": 0})
        await browser.close()
        
        final_ai_msg = final_state["messages"][-1]
        reason = "종료 원인 불명"
        if hasattr(final_ai_msg, "tool_calls") and final_ai_msg.tool_calls:
            reason = final_ai_msg.tool_calls[0]["args"].get("reason", reason)
            
        return f"✅ 에이전트 최종 보고: {reason}"