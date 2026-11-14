"""메모리 에이전트 503 원인 확인용 1회성 진단 (2026-11-02, LuckyBoys 승인).

목적: /api/memory/chat 이 503을 내는 이유가 폴더 이동(import 실패)인지, Gemini 호출 오류인지 가린다.
방법: 1) 에이전트 모듈 import 성공 여부(이동 문제면 여기서 실패)
      2) get_agent_graph() 생성 후 짧은 질의 1회로 실제 예외 종류·메시지 앞부분만 출력(키 값은 출력 안 함)
LLM 호출 1회 비용이 든다. DB에는 쓰지 않는다(graph만 직접 호출).
"""
import asyncio
import json
import traceback

result = {}
try:
    from FastAPI.LangGraph import langgraph_long_term_memory_agent as agent  # 이동 영향 확인 지점
    result["import"] = "ok"
except Exception as error:  # noqa: BLE001 - 진단 목적상 모든 예외를 기록
    result["import"] = f"{type(error).__name__}: {str(error)[:300]}"
    print(json.dumps(result, ensure_ascii=False, indent=1))
    raise SystemExit(1)


async def _probe() -> None:
    try:
        graph = agent.get_agent_graph()
        out = await graph.ainvoke({"messages": [("user", "짧게 '확인'이라고만 답하세요.")], "memory_context": ""},
                                  {"configurable": {"thread_id": "probe-20261102"}})
        result["graph"] = "ok"
        result["response_head"] = str(out.get("verified_response", ""))[:120]
    except Exception as error:  # noqa: BLE001
        result["graph"] = type(error).__name__
        result["message_head"] = str(error)[:400]
        result["trace_tail"] = traceback.format_exc().splitlines()[-6:]


asyncio.run(_probe())
print(json.dumps(result, ensure_ascii=False, indent=1))
