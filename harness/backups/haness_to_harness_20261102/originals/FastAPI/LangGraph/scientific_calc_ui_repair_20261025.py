"""Request a minimal fix for the real calculator browser regression."""
import asyncio,json,os
from pathlib import Path
def main():
    os.environ["SPS_SOURCE_PARTNER_MODEL_PROVIDER"]="gemini"
    from langchain_core.messages import HumanMessage
    from haness.mcp.agents.source_partner_agent import _build_model
    source=Path("haness/apps/scientific_calculator_20261025/scientific_calculator.html").read_text()
    line=next(line for line in source.splitlines() if "getElementById('backspace').onclick=" in line)
    prompt=("Diagnose this actual UI regression and return ONLY JSON "
            "{old:exact existing substring,new:minimal replacement,reason:diagnosis}. "
            "Browser test: calculate 1/0 => result is 오류; click Backspace => "
            "expected result display 0 and input updated, actual result display still 오류. "
            "Keep selection-aware deletion and keyboard focus. Do not change tests, parser or other handlers. "
            "No Markdown. Actual handler:\n"+line)
    async def ask():
        return await asyncio.wait_for(_build_model().ainvoke([HumanMessage(content=prompt)]),timeout=90)
    response=asyncio.run(ask());content=response.content
    text=content if isinstance(content,str) else "\n".join(
        x.get("text","") for x in content if isinstance(x,dict) and x.get("type")=="text")
    result={"model":response.response_metadata.get("model_name"),"proposal_text":text,"original_handler":line}
    Path("harness/memory/scientific_calc_ui_model_proposal_20261025.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
