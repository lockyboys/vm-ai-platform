"""Run Gemini/Ollama through the existing PARTNER model factory and graph.
Process-local provider selection only. The only tool is a read-only sum probe.
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

def main():
    """Execute one explicitly selected provider and preserve its real response."""
    request=json.loads(sys.stdin.read() or "{}")
    provider=request.get("provider")
    if provider not in ("gemini","ollama"):
        raise ValueError("provider must be gemini or ollama")
    # Only this diagnostic process changes; no .env/config/service files are edited.
    os.environ["SPS_SOURCE_PARTNER_MODEL_PROVIDER"]=provider
    import config
    from langchain_core.messages import HumanMessage, ToolMessage
    from langchain_core.tools import tool
    from haness.mcp.agents.source_partner_agent import _build_model, build_source_partner_graph

    @tool
    def arithmetic_probe(a:int,b:int)->str:
        """Read-only diagnostic: return the sum of two integers, without storage."""
        return json.dumps({"a":a,"b":b,"sum":a+b})

    async def run():
        model=_build_model()
        if provider=="ollama" and request.get("tuned") is True:
            # Bounded process-local experiment; production defaults are unchanged.
            model.num_ctx=2048
            model.num_predict=128
            model.reasoning=False
            model.keep_alive="10m"
            result["tuning"]={"num_ctx":2048,"num_predict":128,
                              "reasoning":False,"keep_alive":"10m"}
        graph=build_source_partner_graph(model=model,tools=[arithmetic_probe])
        question="연결 진단입니다. arithmetic_probe 도구를 a=17, b=25로 정확히 한 번 호출하고, 그 결과에 근거해 최종 답변에 합계를 적어 주세요. 다른 작업은 하지 마세요."
        result["question"]=question
        result["runtime_class"]=type(model).__name__
        state=await asyncio.wait_for(
            graph.ainvoke({"messages":[HumanMessage(content=question)]},
                          config={"recursion_limit":8}),
            # 2026-10-31: 하드코딩 90초가 Ollama 응답 전에 먼저 끊어 실패로 오판했다.
            # 루트 config.py의 PARTNER 모델 대기 시간(기본 300초)을 그대로 사용한다(Gemini도 동일 값).
            timeout=config.SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS)
        messages=state.get("messages",[])
        final=messages[-1] if messages else None
        result["answer"]=getattr(final,"content",None)
        result["response_model"]=(getattr(final,"response_metadata",{}) or {}).get("model_name")
        result["usage_metadata"]=getattr(final,"usage_metadata",None)
        result["tool_evidence"]=[
            {"name":m.name,"tool_call_id":m.tool_call_id,"content":m.content}
            for m in messages if isinstance(m,ToolMessage)]
        result["success"]=bool(result["answer"]) and any(
            m["name"]=="arithmetic_probe" and json.loads(m["content"]).get("sum")==42
            for m in result["tool_evidence"])
        result["answer_generation_verified"]=bool(result["answer"])
        result["tool_roundtrip_verified"]=bool(result["tool_evidence"])

    result={"provider":provider,"started_kst":datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "configured_model":config.SPS_MAIN_ORCHESTRATOR_MODEL if provider=="gemini"
                else config.SPS_SOURCE_PARTNER_OLLAMA_MODEL,
            "success":False,"source_or_db_mutation":False,
            "probe":"existing _build_model + build_source_partner_graph with read-only arithmetic tool"}
    started=time.monotonic()
    try:
        asyncio.run(run())
    except Exception as exc:
        result["error_type"]=type(exc).__name__
        result["error"]=str(exc)[:2500]
    result["elapsed_seconds"]=round(time.monotonic()-started,3)
    root=Path(__file__).resolve().parents[2]
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path=root / ("harness/memory/provider_live_probe_"+provider+"_"+stamp+".json")
    with path.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2,default=str)
    print(json.dumps({**result,"evidence":str(path)},ensure_ascii=False,default=str))

if __name__=="__main__":
    main()
