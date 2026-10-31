"""Bounded self-repair loop for the Tetris app, operated through SPS Harness MCP.
Tests are immutable inputs. Only engine.js may change; failure restores its bytes.
"""
import asyncio,difflib,hashlib,json,os,re,shutil,subprocess,sys,tempfile,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/"haness/apps/tetris_stress_20261025"
TESTS=["tests/engine.test.cjs","tests/edge-regressions.test.cjs","tests/stress.test.cjs"]
def run_tests():
    """Run real Node tests and preserve all TAP stdout/stderr, including failures."""
    p=subprocess.run(["node","--test","--test-reporter=tap",*TESTS],cwd=APP,text=True,capture_output=True,timeout=40)
    return {"exit_code":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
def main():
    request=json.loads(sys.stdin.read() or "{}")
    mode=request.get("mode","inspect")
    if mode not in ("inspect","repair"):raise ValueError("Unsupported mode")
    if not shutil.which("node"):raise RuntimeError("Node is unavailable; no source changed")
    started=time.monotonic()
    source_path=APP/"engine.js"
    before=source_path.read_text()
    before_hash=hashlib.sha256(before.encode()).hexdigest()
    test_hashes={name:hashlib.sha256((APP/name).read_bytes()).hexdigest() for name in TESTS}
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    evidence=ROOT/"harness/memory"/("tetris_stress_"+mode+"_"+stamp+".json")
    result={"mode":mode,"before_sha256":before_hash,"test_hashes":test_hashes,
            "baseline":run_tests(),"changed":False}
    if mode=="repair" and result["baseline"]["exit_code"]!=0:
        # This process chooses a provider without changing any service/configuration.
        os.environ["SPS_SOURCE_PARTNER_MODEL_PROVIDER"]="gemini"
        from langchain_core.messages import HumanMessage
        from haness.mcp.agents.source_partner_agent import _build_model
        prompt=("Diagnose the real failing edge tests in this Tetris engine, then propose minimal fixes. "
                "Return ONLY JSON {replacements:[{old:exact nonempty source substring,new:replacement}],reason:string}. "
                "Never modify tests, scoring or gameplay rules. Preserve normal integer moves. "
                "Grid coordinates/offsets must be safe finite integers; reject invalid move inputs without "
                "changing active state or throwing; reject destinations above -active.shape.length "
                "so landing projection cannot perform billions of steps. Exported shape matrices and "
                "their rows must be immutable. No imports, network, eval, new files or global side effects. "
                "Keep browser/Node exports and concise explanatory comments.\nSOURCE:\n"+before+
                "\nACTUAL TEST OUTPUT:\n"+result["baseline"]["stdout"][-16000:])
        async def generate():
            return await asyncio.wait_for(_build_model().ainvoke([HumanMessage(content=prompt)]),timeout=90)
        try:
            response=asyncio.run(generate())
            content=response.content
            text=content if isinstance(content,str) else "\n".join(
                c.get("text","") for c in content if isinstance(c,dict) and c.get("type")=="text")
            text=re.sub(r"^\s*\x60\x60\x60(?:json)?\s*\n","",text)
            text=re.sub(r"\n\s*\x60\x60\x60\s*$","",text)
            proposal=json.loads(text)
            result["model"]=response.response_metadata.get("model_name")
            result["proposal"]=proposal
            replacement=proposal["replacements"]
            if not isinstance(replacement,list) or not 1<=len(replacement)<=6:
                raise ValueError("Expected one to six replacements")
            candidate=before
            for item in replacement:
                old,new=item["old"],item["new"]
                if not isinstance(old,str) or not old or not isinstance(new,str) or candidate.count(old)!=1:
                    raise ValueError("Patch context is ambiguous or absent")
                candidate=candidate.replace(old,new,1)
            if len(candidate)>25000:raise ValueError("Patch exceeds scope")
            with tempfile.TemporaryDirectory(prefix="tetris_patch_check_") as temporary:
                proposed=Path(temporary)/"engine.js";proposed.write_text(candidate)
                syntax=subprocess.run(["node","--check",str(proposed)],text=True,capture_output=True,timeout=10)
                result["dry_run"]={"syntax_exit_code":syntax.returncode,"stderr":syntax.stderr}
                if syntax.returncode:raise ValueError("Proposed source has invalid syntax")
            if source_path.read_text()!=before:raise RuntimeError("Concurrent source change")
            if any(hashlib.sha256((APP/name).read_bytes()).hexdigest()!=value for name,value in test_hashes.items()):
                raise RuntimeError("Test contract changed")
            backup=ROOT/"harness/memory"/("tetris_stress_engine_before_"+stamp+".js.txt")
            backup.write_text(before);result["backup"]=str(backup)
            result["patch"]="".join(difflib.unified_diff(before.splitlines(True),candidate.splitlines(True),
                                                        fromfile="before/engine.js",tofile="after/engine.js"))
            source_path.write_text(candidate)
            try:
                result["after"]=run_tests()
                if result["after"]["exit_code"]!=0:raise RuntimeError("Regression failed")
                result["changed"]=True
                result["after_sha256"]=hashlib.sha256(candidate.encode()).hexdigest()
            except BaseException:
                source_path.write_text(before)
                result["rolled_back"]=True
                raise
        except Exception as error:
            result["error_type"]=type(error).__name__;result["error"]=str(error)[:2000]
    result["elapsed_seconds"]=round(time.monotonic()-started,3)
    evidence.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    def summary(log):
        return {"exit_code":log["exit_code"],"counts":re.findall(r"^# (?:tests|pass|fail|skipped) .*",log["stdout"],re.M)}
    print(json.dumps({"mode":mode,"changed":result["changed"],"before":summary(result["baseline"]),
                      "after":summary(result["after"]) if "after" in result else None,
                      "model":result.get("model"),"error":result.get("error"),"evidence":str(evidence),
                      "elapsed_seconds":result["elapsed_seconds"]},ensure_ascii=False))
if __name__=="__main__":main()
