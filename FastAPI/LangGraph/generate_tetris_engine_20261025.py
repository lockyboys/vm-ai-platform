"""Generate a standalone Tetris engine with the explicitly requested Gemini model."""
import asyncio,json,sys
from pathlib import Path
def main():
    request=json.loads(sys.stdin.read())
    import os
    os.environ["SPS_SOURCE_PARTNER_MODEL_PROVIDER"]="gemini"
    from langchain_core.messages import HumanMessage
    from haness.mcp.agents.source_partner_agent import _build_model
    async def run():
        return await asyncio.wait_for(_build_model().ainvoke([HumanMessage(content=request["prompt"])]),timeout=90)
    response=asyncio.run(run())
    content=response.content
    source=content if isinstance(content,str) else "\n".join(x.get("text","") for x in content if isinstance(x,dict) and x.get("type")=="text")
    result={"source":source,"response_model":response.response_metadata.get("model_name"),
            "usage":getattr(response,"usage_metadata",None)}
    Path("harness/memory/tetris_engine_generation_20261025.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":
    main()
