"""Durable launcher/status for explicitly approved autonomous production-source repair.
Existing PARTNER tools own source patch, pytest, staging and rollback.
"""
import asyncio, hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"harness/memory/autonomous_operational_repair_attempt5_20261025"
def main():
    request=json.loads(sys.stdin.read() or "{}")
    mode=request.get("mode","status")
    state=Path(str(BASE)+"_state.json")
    output=Path(str(BASE)+"_result.json")
    if mode=="cancel":
        # Stop only this verified diagnostic process group, never a service.
        import signal
        metadata=json.loads(state.read_text()) if state.exists() else {}
        pid=metadata.get("pid")
        stopped=False
        if pid:
            try:
                command=Path(f"/proc/{pid}/cmdline").read_bytes()
                if b"run_autonomous_operational_repair_attempt5_20261025.py" in command and os.getpgid(pid)==pid:
                    os.killpg(pid,signal.SIGTERM)
                    stopped=True
            except (ProcessLookupError,FileNotFoundError):
                pass
        print(json.dumps({"cancel_requested":stopped,"result_exists":output.exists()}))
        return
    if mode=="status":
        result={"state":json.loads(state.read_text()) if state.exists() else None,
                "result":json.loads(output.read_text()) if output.exists() else None}
        print(json.dumps(result,ensure_ascii=False,default=str))
        return
    if mode=="start":
        if state.exists():
            print(json.dumps({"existing_job":True,"state":json.loads(state.read_text()),
                              "result_exists":output.exists()},ensure_ascii=False))
            return
        task=request["task"]
        task_path=Path(str(BASE)+"_task.txt")
        task_path.write_text(task,encoding="utf-8")
        # Durable subprocess avoids holding an MCP request during model/tool loops.
        log=Path(str(BASE)+"_worker.log")
        with log.open("x") as stream:
            process=subprocess.Popen(
                [sys.executable,str(ROOT/"FastAPI/LangGraph/run_autonomous_operational_repair_attempt5_20261025.py")],
                cwd=ROOT,stdin=subprocess.PIPE,stdout=stream,stderr=stream,
                start_new_session=True,text=True)
            process.stdin.write(json.dumps({"mode":"worker"}))
            process.stdin.close()
        metadata={"pid":process.pid,"started_utc":datetime.now(timezone.utc).isoformat(),
                  "task_sha256":hashlib.sha256(task.encode()).hexdigest(),
                  "provider":"gemini","status":"RUNNING","result_path":str(output),"log":str(log)}
        with state.open("x") as stream:
            json.dump(metadata,stream,ensure_ascii=False,indent=2)
        print(json.dumps(metadata,ensure_ascii=False))
        return
    if mode!="worker":
        raise ValueError("Unknown mode")
    # Only this process selects Gemini; no configuration file/service changes.
    os.environ["SPS_SOURCE_PARTNER_MODEL_PROVIDER"]="gemini"
    from haness.mcp.agents import source_partner_agent as agent
    from langchain_core.callbacks import BaseCallbackHandler
    class Trace(BaseCallbackHandler):
        """Persist actual model/tool operations, including failed tool calls."""
        def record(self,kind,value):
            with Path(str(BASE)+"_trace.jsonl").open("a") as stream:
                stream.write(json.dumps({"event":kind,"value":str(value)[:16000]},ensure_ascii=False)+"\n")
        def on_tool_start(self,serialized,input_str,**kwargs):
            self.record("tool_start",{"name":serialized.get("name"),"input":input_str})
        def on_tool_end(self,output,**kwargs):
            self.record("tool_end",output)
        def on_tool_error(self,error,**kwargs):
            self.record("tool_error",error)
    # Diagnostic recovery adapter only: preserve path restrictions while returning
    # failed tools as errors so the model can repair the real unmodified source.
    # Fresh pytest processes do not inherit this temporary adapter.
    from functools import partial
    real_tool_node=agent.ToolNode
    agent.ToolNode=partial(real_tool_node,handle_tool_errors=True)
    original_builder=agent.build_source_partner_graph
    def traced_builder(**kwargs):
        compiled=original_builder(**kwargs)
        class BudgetedGraph:
            async def ainvoke(self, state, config=None):
                # This diagnostic needs investigation + reproduction + repair, within 600s.
                options=dict(config or {})
                options.update(recursion_limit=64,callbacks=[Trace()])
                return await compiled.ainvoke(state,config=options)
        return BudgetedGraph()
    agent.build_source_partner_graph=traced_builder
    run_source_partner_agent=agent.run_source_partner_agent
    try:
        result=asyncio.run(asyncio.wait_for(
            run_source_partner_agent(Path(str(BASE)+"_task.txt").read_text(),
                                     dry_run=False,source_write_confirmed=True,
                                     commit_confirmed=False),timeout=600))
    except Exception as exc:
        result={"success":False,"error_type":type(exc).__name__,"error":str(exc)}
    result["finished_utc"]=datetime.now(timezone.utc).isoformat()
    with output.open("x") as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2,default=str)
if __name__=="__main__":
    main()
