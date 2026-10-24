# sps_langgraph_mcp.py
# [목적] LangGraph 기반 순환 에이전트 (48개 MCP 도구 지원 및 DB 직결)
from typing import TypedDict, Annotated, Sequence
import operator
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# 공통 DB 연동
from common.database import get_mariadb_connection, get_mongodb_client, MariaMongoWriteService
from config import settings

# (가정) LangChain 호환 48개 도구 로드 및 ToolNode 유틸리티
from haness.mcp_client import get_langchain_48_tools
from langgraph.prebuilt import ToolNode

# 1. 상태 정의
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    object_id: int
    memory_saved: bool

# 2. 노드 1: 에이전트 추론 (Ollama)
def agent_node(state: AgentState):
    print("--- [Node] 에이전트 추론 ---")
    messages = state["messages"]
    # 48개 도구 동적 주입 (bind_tools)
    tools = get_langchain_48_tools() 
    
    # [주의점] 실제 Ollama 모델 래퍼로 교체 (ChatOllama 등)
    # response = llm.bind_tools(tools).invoke(messages)
    mock_response = AIMessage(content="추론 결과", additional_kwargs={"tool_calls": []})
    return {"messages": [mock_response]}

# 3. 노드 2: 48개 도구 실행 노드 (ToolNode 활용)
# [이유] LangGraph prebuilt ToolNode에 48개 배열을 넘기면 알아서 매칭하여 실행합니다.
all_48_tools = get_langchain_48_tools()
tools_node = ToolNode(all_48_tools)

# 4. 노드 3: 하이브리드 DB 저장
def save_memory_node(state: AgentState):
    print("--- [Node] 하이브리드 DB 장기 기억 저장 ---")
    maria_conn = get_mariadb_connection()
    mongo_client = get_mongodb_client()
    db_service = MariaMongoWriteService(maria_conn, mongo_client)
    
    # 마지막 메시지 추출
    last_message = state["messages"][-1].content
    initial_query = state["messages"][0].content if state["messages"] else ""
    
    try:
        success = db_service.execute_hybrid_workflow(
            obj_id=state.get("object_id", 0),
            query_data=initial_query,
            gemini_result={"final_answer": last_message},
            has_evidence=True
        )
        return {"memory_saved": success}
    except Exception as e:
        print(f"[Error] DB 롤백 발생: {e}")
        return {"memory_saved": False}
    finally:
        maria_conn.close()
        mongo_client.close()

# 5. 분기 조건 (도구를 호출할 것인가, 종료(저장)할 것인가?)
def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "save_memory"

# 6. Graph 빌드 및 컴파일
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_node)
workflow.add_node("save_memory", save_memory_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "save_memory": "save_memory"})
workflow.add_edge("tools", "agent") # 도구 실행 후 다시 에이전트로
workflow.add_edge("save_memory", END)

app = workflow.compile()

# 실행 예시: 
# inputs = {"messages": [HumanMessage(content="내 이름은 Luckyboys야")], "object_id": 123}
# result = app.invoke(inputs)