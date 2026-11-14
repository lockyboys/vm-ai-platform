# sps_gemini_agent.py
# [목적] FastAPI 기반 Gemini 에이전트 엔드포인트 (48개 MCP 도구 지원 및 DB 직결)
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

# 공통 DB 커넥션 및 하이브리드 적재 서비스
from common.database import get_mariadb_connection, get_mongodb_client, MariaMongoWriteService
from config import settings

# (가정) 48개의 MCP 도구를 동적으로 가져오는 함수
from haness.mcp_client import get_all_48_mcp_tools, execute_mcp_tool

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    thread_id: str
    subject_id: str
    object_id: int  # 사전에 채번된 sp_object ID

@router.post("/api/gemini/chat")
async def gemini_chat_endpoint(request: ChatRequest):
    maria_conn = get_mariadb_connection()
    mongo_client = get_mongodb_client()
    db_service = MariaMongoWriteService(maria_conn, mongo_client)
    
    try:
        # 1. 48개 도구 동적 로드
        # [이유] 하드코딩 없이 확장 가능한 도구 생태계 구성
        available_tools = get_all_48_mcp_tools()
        
        # 2. Gemini API 호출 (도구 목록 주입)
        # (실제 Gemini SDK 호출 로직으로 치환)
        gemini_response = mock_gemini_call(request.query, tools=available_tools)
        
        # 3. 함수 호출(Function Calling) 여부 확인 및 48개 도구 동적 실행
        tool_execution_logs = []
        if gemini_response.get("tool_calls"):
            for tool_call in gemini_response["tool_calls"]:
                tool_result = execute_mcp_tool(tool_call["name"], tool_call["arguments"])
                tool_execution_logs.append({"tool": tool_call["name"], "result": tool_result})
                
            # 도구 실행 결과를 바탕으로 Gemini 재호출 (최종 응답 생성)
            gemini_response = mock_gemini_call("도구 결과를 요약해줘", context=tool_execution_logs)

        # 4. 하이브리드 DB 적재 (MariaDB + MongoDB)
        # [주의점] 에이전트가 실행한 쿼리, 결과, 도구 사용 이력을 몽고DB 페이로드에 모두 담아 적재
        final_payload = {
            "reply": gemini_response["text"],
            "tool_logs": tool_execution_logs
        }
        
        success = db_service.execute_hybrid_workflow(
            obj_id=request.object_id,
            query_data=request.query,
            gemini_result=final_payload,
            has_evidence=len(tool_execution_logs) > 0
        )
        
        return {
            "status": "success",
            "reply": gemini_response["text"],
            "memory_saved": success
        }
        
    except Exception as e:
        print(f"[Error] Gemini Agent 예외 발생: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        maria_conn.close()
        mongo_client.close()

def mock_gemini_call(query: str, tools: List=None, context: Any=None):
    # Gemini SDK 연동 대체용 Mock
    return {"text": f"'{query}'에 대한 완벽한 처리 완료", "tool_calls": [{"name": "tool_1", "arguments": {}}]}