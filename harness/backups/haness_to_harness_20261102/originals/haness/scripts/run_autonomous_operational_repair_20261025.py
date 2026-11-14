"""Durable launcher/status for explicitly approved autonomous production-source repair.
Existing PARTNER tools own source patch, pytest, staging and rollback.
"""
import asyncio, hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"harness/memory/autonomous_operational_repair_20261025"
def main():
    request=json.loads(sys.stdin.read() or "{}")
    mode=request.get("mode","status")
    state=Path(str(BASE)+"_state.json")
    output=Path(str(BASE)+"_result.json")
    if mode=="status":
        result={"state":json.loads(state.read_text()) if state.exists() else None,
                "result":json.loads(output.read_text()) if output.exists() else None}
        # A saved RUNNING label alone cannot prove that a child survived its launcher.
        result["process_alive"]=False
        if result["state"]:
            pid=result["state"]["pid"]
            try:
                cmdline=Path(f"/proc/{pid}/cmdline").read_bytes()
                result["process_alive"]=b"run_autonomous_operational_repair_20261025.py" in cmdline
            except FileNotFoundError:
                pass
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
                [sys.executable,str(ROOT/"FastAPI/LangGraph/run_autonomous_operational_repair_20261025.py")],
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
    from haness.mcp.agents.source_partner_agent import run_source_partner_agent
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
