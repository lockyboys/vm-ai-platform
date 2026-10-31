"""Durable invocation of the existing SPS orchestrator; no fixed persona sequence."""
import asyncio,functools,hashlib,json,os,subprocess,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"harness/memory/orchestrator_delegated_integration_20261025"
def main():
    request=json.loads(sys.stdin.read() or "{}")
    mode=request.get("mode","status")
    result_path=BASE.with_name(BASE.name+"_result.json")
    state_path=BASE.with_name(BASE.name+"_state.json")
    if mode=="status":
        state=json.loads(state_path.read_text()) if state_path.exists() else {}
        result=json.loads(result_path.read_text()) if result_path.exists() else None
        trace=BASE.with_name(BASE.name+"_trace.jsonl")
        lines=trace.read_text().splitlines() if trace.exists() else []
        print(json.dumps({"state":state,"result":result,"trace_events":len(lines),
                          "last_event":json.loads(lines[-1]) if lines else None},ensure_ascii=False));return
    if mode=="start":
        if state_path.exists():
            print(json.dumps({"existing_job":True,"state":json.loads(state_path.read_text())}));return
        query=request["query"]
        BASE.with_name(BASE.name+"_query.json").write_text(query)
        with BASE.with_name(BASE.name+"_worker.log").open("x") as log:
            process=subprocess.Popen([sys.executable,str(ROOT/"FastAPI/LangGraph/orchestrator_delegated_integration_20261025.py")],
                cwd=ROOT,stdin=subprocess.PIPE,stdout=log,stderr=log,start_new_session=True,text=True)
            process.stdin.write('{"mode":"worker"}');process.stdin.close()
        state={"pid":process.pid,"started_utc":datetime.now(timezone.utc).isoformat(),
               "query_sha256":hashlib.sha256(query.encode()).hexdigest(),"runtime_seconds":600,"recursion_limit":64}
        state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2))
        print(json.dumps(state));return
    if mode!="worker":raise ValueError("Unknown mode")
    from haness.mcp.tools import orchestrator_tools
    from haness.mcp.agents import source_partner_agent as agent
    from langchain_core.callbacks import BaseCallbackHandler
    class Trace(BaseCallbackHandler):
        def record(self,event,data):
            with BASE.with_name(BASE.name+"_trace.jsonl").open("a") as stream:
                stream.write(json.dumps({"time":datetime.now(timezone.utc).isoformat(),
                    "event":event,"data":str(data)[:24000]},ensure_ascii=False)+"\n")
        def on_tool_start(self,serialized,input_str,**kwargs):
            self.record("tool_start",{"name":serialized.get("name"),"input":input_str})
        def on_tool_end(self,output,**kwargs):self.record("tool_end",output)
        def on_tool_error(self,error,**kwargs):self.record("tool_error",error)
    original_builder=agent.build_source_partner_graph
    def traced_builder(**kwargs):
        graph=original_builder(**kwargs)
        class TracedGraph:
            async def ainvoke(self,state,config=None):
                return await graph.ainvoke(state,config={**(config or {}),"callbacks":[Trace()]})
        return TracedGraph()
    agent.build_source_partner_graph=traced_builder
    # Only the invocation budget changes; role selection belongs to SPS.
    orchestrator_tools._run_source_partner_agent=functools.partial(agent.run_source_partner_agent,recursion_limit=64)
    try:
        result=asyncio.run(asyncio.wait_for(orchestrator_tools.run_sps_orchestrator(
            BASE.with_name(BASE.name+"_query.json").read_text(),dry_run=False),timeout=600))
    except Exception as error:
        result={"success":False,"error_type":type(error).__name__,"error":str(error)}
    result["finished_utc"]=datetime.now(timezone.utc).isoformat()
    result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str))
if __name__=="__main__":main()
