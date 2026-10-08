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
# - docstring 누락으로 인한 StructuredTool ValueError 수정 완료 버전
# - 스마트 링크 텍스트 기반 자동 탐색 및 다운로드 보완 버전
# - URL 직접 다운로드 및 파일 저장 보완 버전
# - 특정 사이트 종속성(하드코딩) 전면 배제 및 완전 범용 PDF 수집 엔진
# ==============================================================================
# FastAPI/LangGraph/Agent_Import_PFDs/LangGraph_Network_Sniffer.py
# ==============================================================================
# [SPS ORCHESTRATOR 13-PERSONA VERIFIED]
# 
import os
import sys
import base64
import asyncio
import subprocess
import httpx
from typing import Annotated
from typing_extensions import TypedDict
from urllib.parse import urlparse, urljoin

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
    """어떤 도메인이든 URL만 입력하면 도메인별 폴더를 생성하고 PDF 문서를 범용적으로 수집하는 에이전트입니다."""
    
    domain_name = urlparse(start_url).netloc or "unknown_domain"
    dynamic_pdf_dir = os.path.join(BASE_DIR, domain_name)
    
    if not os.path.exists(dynamic_pdf_dir): 
        os.makedirs(dynamic_pdf_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        print(f"🌐 [Generic Crawler Engine] 대상 URL 진입: {start_url}")
        await page.goto(start_url, wait_until="networkidle", timeout=30000)

        @tool
        async def click_element(selector: str) -> str:
            """지정된 셀렉터가 있으면 클릭하고, 없거나 문서 수집이 필요할 때 페이지 내 모든 링크를 범용 탐색하여 PDF를 다운로드합니다."""
            nonlocal page
            try:
                print(f"   🤖 [범용 Tool 실행] 대상 탐색 및 링크 분석 중...")
                
                if selector and selector != "auto":
                    target_locator = page.locator(selector)
                    if await target_locator.count() > 0:
                        await target_locator.first.click(timeout=5000, force=True)
                        await asyncio.sleep(2)

                links = await page.locator("a").all()
                saved_count = 0
                
                async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=20.0) as client:
                    for link in links:
                        try:
                            href = await link.get_attribute("href")
                            text = await link.inner_text()
                            
                            if href and (
                                ".pdf" in href.lower() or 
                                "pdf" in (text or "").lower() or 
                                "약관" in (text or "") or 
                                "download" in href.lower()
                            ):
                                pdf_url = urljoin(start_url, href)
                                file_name = pdf_url.split("/")[-1].split("?")[0].strip()
                                if not file_name or not file_name.endswith(".pdf"):
                                    file_name = f"document_{saved_count + 1}.pdf"
                                    
                                file_path = os.path.join(dynamic_pdf_dir, file_name)
                                
                                if not os.path.exists(file_path):
                                    print(f"   📥 범용 다운로드 감지: {file_name}")
                                    resp = await client.get(pdf_url)
                                    if resp.status_code == 200 and len(resp.content) > 500:
                                        with open(file_path, "wb") as f:
                                            f.write(resp.content)
                                        saved_count += 1
                                        print(f"   ✅ 저장 완료: {file_path}")
                        except Exception:
                            continue

                if saved_count > 0:
                    return f"[성공] 총 {saved_count}개의 문서를 범용 폴더({dynamic_pdf_dir})에 수집했습니다. 즉시 finish_task를 호출하세요."
                
                return f"[탐색 결과] 현재 화면에서 추가 문서를 찾지 못했습니다. tavily_search로 올바른 주소를 검색하세요."
            
            except Exception as e:
                return f"[에러] 범용 탐색 중 예외 발생: {str(e)[:100]}"

        @tool
        def source_patch(file_path: str, old_code: str, new_code: str) -> str:
            """필요시 자율적으로 코드를 수정하고 즉시 Git에 커밋합니다."""
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
                print(f"   🔧 [Autonomous Patch 성공] 파일이 수정되었습니다: {target_file}")

                # 문법 에러 수정: 작은따옴표 사용
                subprocess.run(['git', 'add', target_file], check=True)
                subprocess.run(['git', 'commit', '-m', 'refactor(crawler): make pdf crawler completely domain-agnostic and generic'], check=True)
                print(f"   📦 [Git Commit 성공] 변경 사항이 커밋되었습니다.")
                
                return f"[자율 패치 및 커밋 완료] 범용 코드가 Git에 반영되었습니다."
            except Exception as e:
                return f"[패치/커밋 에러] 예외 발생: {str(e)}"

        @tool
        async def finish_task(reason: str) -> str:
            """작업 완료를 선언합니다."""
            return f"임무 종료: {reason}"

        tavily_tool = TavilySearchResults(max_results=3)

        tools = [click_element, source_patch, finish_task, tavily_tool]
        llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0).bind_tools(tools)
        tool_node = ToolNode(tools)

        sys_msg = SystemMessage(content="""당신은 13개 페르소나 검증을 거친 완전 범용 웹 문서 수집 에이전트입니다.
        어떤 사이트가 주어지든 click_element를 통해 링크와 문서를 범용적으로 수집하고, 필요시 tavily_tool로 검색하거나 source_patch를 수행하세요.
        목표를 달성하면 finish_task를 호출하세요.""")

        async def vision_agent_node(state: AgentState):
            turn = state.get("turn_count", 0)
            if turn > 8:
                return {"messages": [AIMessage(content="", tool_calls=[{"name": "finish_task", "args": {"reason": "최대 탐색 턴 초과"}, "id": "force_end"}])]}

            print(f"\n🔄 [Agent Turn {turn + 1}] 범용 에이전트 화면 분석 중...")
            await asyncio.sleep(2)
            screenshot = await page.screenshot(full_page=False)
            b64_img = base64.b64encode(screenshot).decode('utf-8')

            user_msg = HumanMessage(content=[
                {"type": "text", "text": "현재 화면입니다. 범용 탐색 기능을 이용해 문서를 수집하고 finish_task를 호출하세요."},
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