"""SPS calculator generation / test / bounded-repair pipeline.
Independent tests are immutable; only the app engine may be generated/repaired.
"""
import asyncio,difflib,hashlib,json,os,re,shutil,subprocess,sys,tempfile,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/"haness/apps/scientific_calculator_20261025"
TESTS=["tests/engine.test.cjs","tests/stress.test.cjs"]
CONTRACT="""Create a dependency-free JS scientific-calculator engine, export {evaluate} as module.exports and globalThis.CalculatorCore. evaluate(expression,angleMode='deg') returns a finite Number or throws Error. Reject non-string, empty, >500-character, >256-token inputs and parser recursion >32. Use a proper tokenizer and recursive-descent/Pratt parser, NEVER eval, Function, require, imports, DOM, network or dynamic execution. Support decimal/scientific numbers, whitespace, case-insensitive names, constants pi/e and Unicode pi, normalize Unicode × ÷ −. No implicit multiplication. Operators + - * /, powers ^ and ** (right associative), unary signs LOWER precedence than powers, higher than addition; postfix factorial ! and percentage % (= divide by100, NOT binary modulo). -2^2=-4; 2^-2=.25; 2^3!=64. Functions EXACT ARITY: sin cos tan asin acos atan sqrt abs ln log10 exp floor ceil round factorial (1 argument each), log(x,base) (2). Inverse trig returns the selected angle unit; ordinary trig takes that unit. Reject zero division, negative sqrt/nonpositive log, log base <=0 or1, inverse domain violations, tan at undefined odd90deg/pi/2 (cos near0 threshold1e-12), nonfinite results, factorial nonintegers/negative/>170, unknown identifiers or trailing tokens. Keep all calculations finite and bounded. Do not accept properties/arrays/objects/strings/comments. Error messages concise in Korean or English. Include concise comments. Return JS source only, no Markdown."""
def node(*args,cwd=APP):
    p=subprocess.run([shutil.which("node"),*args],cwd=cwd,
        env={"PATH":os.defpath},text=True,capture_output=True,timeout=25)
    return {"exit_code":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
def clean(text):
    text=re.sub(r"^\s*\x60\x60\x60(?:javascript|js|json)?\s*\n","",text)
    return re.sub(r"\n\s*\x60\x60\x60\s*$","",text).strip()
def main():
    request=json.loads(sys.stdin.read() or "{}");mode=request.get("mode","inspect")
    if mode not in ("generate","inspect","repair"):raise ValueError("Bad mode")
    if not shutil.which("node"):raise RuntimeError("Node not installed")
    engine=APP/"engine.js";before=engine.read_text() if engine.exists() else None
    tests={name:hashlib.sha256((APP/name).read_bytes()).hexdigest() for name in TESTS}
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    evidence=ROOT/"harness/memory"/("scientific_calc_"+mode+"_"+stamp+".json")
    result={"mode":mode,"test_hashes":tests,"changed":False}
    start=time.monotonic()
    if mode!="generate":
        if before is None:raise RuntimeError("Generate engine first")
        result["before"]=node("--test","--test-reporter=tap",*TESTS)
    need_model=(mode=="generate" and before is None) or (mode=="repair" and result["before"]["exit_code"]!=0)
    if need_model:
        os.environ["SPS_SOURCE_PARTNER_MODEL_PROVIDER"]="gemini"
        from langchain_core.messages import HumanMessage
        from haness.mcp.agents.source_partner_agent import _build_model
        prompt=CONTRACT+"\nIndependent acceptance tests:\n"+(APP/TESTS[0]).read_text()
        if mode=="repair":
            prompt=("Repair this calculator to the contract and unchanged tests. Return ONLY JSON "
                    "{replacements:[{old:exact existing substring,new:replacement}],reason:string}. "
                    "No test edits.\n"+CONTRACT+"\nSOURCE:\n"+before+
                    "\nACTUAL FAILURES:\n"+result["before"]["stdout"][-18000:])
        async def generate():
            return await asyncio.wait_for(_build_model().ainvoke([HumanMessage(content=prompt)]),timeout=90)
        try:
            response=asyncio.run(generate());content=response.content
            answer=content if isinstance(content,str) else "\n".join(
                c.get("text","") for c in content if isinstance(c,dict) and c.get("type")=="text")
            result.update(model=response.response_metadata.get("model_name"),model_answer=answer)
            answer=clean(answer)
            if mode=="generate":candidate=answer+"\n"
            else:
                proposal=json.loads(answer);result["proposal"]=proposal;candidate=before
                if not 1<=len(proposal["replacements"])<=8:raise ValueError("Too many replacements")
                for edit in proposal["replacements"]:
                    if not edit["old"] or candidate.count(edit["old"])!=1:raise ValueError("Patch context mismatch")
                    candidate=candidate.replace(edit["old"],edit["new"],1)
            if len(candidate)>24000 or re.search(r"\b(?:eval|Function|require|fetch)\s*\(|\bimport\b|process\.",candidate):
                raise ValueError("Forbidden dynamic execution or source size")
            with tempfile.TemporaryDirectory() as temporary:
                path=Path(temporary)/"engine.js";path.write_text(candidate)
                syntax=node("--check",str(path));result["dry_run"]=syntax
                if syntax["exit_code"]:raise ValueError("Invalid JS syntax")
            if (engine.read_text() if engine.exists() else None)!=before:raise ValueError("Concurrent edit")
            result["source_before"]=before
            if before is not None:
                result["patch"]="".join(difflib.unified_diff(before.splitlines(True),candidate.splitlines(True),
                                                           fromfile="before/engine.js",tofile="after/engine.js"))
            engine.write_text(candidate)
            result["after"]=node("--test","--test-reporter=tap",*TESTS)
            if any(hashlib.sha256((APP/n).read_bytes()).hexdigest()!=h for n,h in tests.items()):
                raise RuntimeError("Test contract changed")
            # Preserve first generated source even when tests fail so repair can diagnose it.
            if mode=="repair" and result["after"]["exit_code"]!=0:
                engine.write_text(before);result["rolled_back"]=True
            else:result["changed"]=True
            result["source_after"]=candidate
        except Exception as error:
            if mode=="repair" and before is not None and engine.exists() and engine.read_text()!=before:
                engine.write_text(before);result["rolled_back"]=True
            result.update(error_type=type(error).__name__,error=str(error)[:2000])
    result["elapsed_seconds"]=round(time.monotonic()-start,3)
    if engine.exists():result["engine_sha256"]=hashlib.sha256(engine.read_bytes()).hexdigest()
    evidence.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    summary={k:{"exit_code":result[k]["exit_code"],"counts":re.findall(r"^# (?:tests|pass|fail|skipped) .*",result[k]["stdout"],re.M)}
             for k in ("before","after") if k in result}
    print(json.dumps({"mode":mode,"changed":result["changed"],"model":result.get("model"),
                      "tests":summary,"error":result.get("error"),"evidence":str(evidence),
                      "elapsed_seconds":result["elapsed_seconds"]},ensure_ascii=False))
if __name__=="__main__":main()
