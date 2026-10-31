"""Isolated model repair benchmark; no production writes or DB calls."""
import ast, asyncio, difflib, json, os, re, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
BROKEN='def clamp(value, lower, upper):\n    """Clamp inclusively; reject reversed bounds."""\n    return min(lower, max(upper, value))\n'
TESTS='''import pytest
from clamp_module import clamp
@pytest.mark.parametrize("v,lo,hi,want",[(5,0,10,5),(-1,0,10,0),(11,0,10,10),(0,0,10,0),(10,0,10,10),(-3,-5,-1,-3),(4,4,4,4)])
def test_bounds(v,lo,hi,want):
    assert clamp(v,lo,hi)==want
def test_reversed():
    with pytest.raises(ValueError):
        clamp(5,10,0)
'''
def safe(code):
    """Accept one pure clamp function, with no imports, attributes or I/O."""
    if len(code)>2000: raise ValueError("Code too long")
    tree=ast.parse(code)
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef):
        raise ValueError("Expected one function")
    fn=tree.body[0]
    if fn.name!="clamp" or [x.arg for x in fn.args.args]!=["value","lower","upper"] or fn.decorator_list:
        raise ValueError("Changed signature")
    allowed=(ast.Module,ast.FunctionDef,ast.arguments,ast.arg,ast.Expr,ast.Constant,ast.Return,
             ast.If,ast.Compare,ast.Gt,ast.GtE,ast.Lt,ast.LtE,ast.Eq,ast.NotEq,ast.Load,
             ast.Name,ast.Call,ast.Raise,ast.UnaryOp,ast.USub,ast.UAdd,ast.BoolOp,ast.And,ast.Or)
    for n in ast.walk(tree):
        if not isinstance(n,allowed): raise ValueError("Forbidden AST "+type(n).__name__)
        if isinstance(n,ast.Name) and n.id not in ("value","lower","upper","min","max","ValueError"):
            raise ValueError("Forbidden name")
        if isinstance(n,ast.Call) and (not isinstance(n.func,ast.Name) or n.func.id not in ("min","max","ValueError")):
            raise ValueError("Forbidden call")
    return code
def pytest_run(path):
    """Use fixed acceptance tests, no project plugins, no inherited secrets."""
    p=subprocess.run([sys.executable,"-m","pytest","-q","test_clamp.py"],cwd=path,
        env={"PATH":os.defpath,"PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1","PYTHONDONTWRITEBYTECODE":"1"},
        text=True,capture_output=True,timeout=10)
    return {"exit_code":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
def main():
    request=json.loads(sys.stdin.read() or "{}")
    provider=request["provider"]
    if provider not in ("gemini","ollama"): raise ValueError("Bad provider")
    os.environ["SPS_SOURCE_PARTNER_MODEL_PROVIDER"]=provider
    import config
    from langchain_core.messages import HumanMessage
    from haness.mcp.agents.source_partner_agent import _build_model
    result={"provider":provider,"success":False,"fixture_before":BROKEN,"tests":TESTS}
    start=time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="sps_model_repair_") as tmp:
            path=Path(tmp)
            (path/"clamp_module.py").write_text(BROKEN)
            (path/"test_clamp.py").write_text(TESTS)
            result["before_tests"]=pytest_run(path)
            if result["before_tests"]["exit_code"]!=1: raise RuntimeError("Baseline must fail")
            model=_build_model()
            result["configured_model"]=model.model
            if provider=="ollama":
                # Bounded tuning experiment only; no persistent settings are changed.
                model.num_ctx=2048
                model.num_predict=256
                model.reasoning=False
                model.keep_alive="10m"
                result["tuning"]={"num_ctx":2048,"num_predict":256,"reasoning":False,"keep_alive":"10m"}
            prompt=("Fix clamp: preserve values inside inclusive bounds; return nearest bound outside; "
                    "raise ValueError if lower > upper. Keep def clamp(value, lower, upper) and its docstring. "
                    "Return only Python, no Markdown, no imports/extra functions.\n"+BROKEN+"\nTESTS:\n"+TESTS)
            async def generate():
                return await asyncio.wait_for(model.ainvoke([HumanMessage(content=prompt)]),timeout=90)
            response=asyncio.run(generate())
            content=response.content
            answer=content if isinstance(content,str) else "\n".join(
                b.get("text","") for b in content if isinstance(b,dict) and b.get("type")=="text")
            result["model_answer"]=answer
            result["response_model"]=(response.response_metadata or {}).get("model_name")
            result["usage_metadata"]=getattr(response,"usage_metadata",None)
            code=re.sub(r"^\s*\x60\x60\x60(?:python)?\s*\n","",answer)
            code=re.sub(r"\n\s*\x60\x60\x60\s*$","",code).strip()+"\n"
            repaired=safe(code)
            result["fixture_after"]=repaired
            result["diff"]="".join(difflib.unified_diff(BROKEN.splitlines(True),repaired.splitlines(True)))
            (path/"clamp_module.py").write_text(repaired)
            result["after_tests"]=pytest_run(path)
            result["success"]=result["after_tests"]["exit_code"]==0
    except Exception as exc:
        result.update(error_type=type(exc).__name__,error=str(exc)[:2000])
    result["elapsed_seconds"]=round(time.monotonic()-start,3)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out=Path("harness/memory")/("provider_repair_"+provider+"_"+stamp+".json")
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    print(json.dumps({**result,"evidence":str(out)},ensure_ascii=False,default=str))
if __name__=="__main__":
    main()
