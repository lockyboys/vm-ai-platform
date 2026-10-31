"""Ask Ollama for a minimal repair of an explicitly injected Tetris-copy defect."""
import asyncio,json,sys
from pathlib import Path
def main():
    request=json.loads(sys.stdin.read())
    import os
    os.environ["SPS_SOURCE_PARTNER_MODEL_PROVIDER"]="ollama"
    from langchain_core.messages import HumanMessage
    from haness.mcp.agents.source_partner_agent import _build_model
    model=_build_model()
    model.reasoning=False
    model.num_ctx=2048
    model.num_predict=192
    model.keep_alive="10m"
    async def run():
        return await asyncio.wait_for(model.ainvoke([HumanMessage(content=request["prompt"])]),timeout=90)
    r=asyncio.run(run())
    result={"answer":r.content,"model":r.response_metadata.get("model_name"),
            "usage":getattr(r,"usage_metadata",None)}
    Path("harness/memory/tetris_ollama_fault_repair_20261025.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":
    main()
