"""Fresh-process entry for the existing SPS orchestrator's dynamic source mode."""
import asyncio,hashlib,json,shutil,sys
from pathlib import Path
import config
from common.common_function import now_kst_iso
ROOT=Path(__file__).resolve().parents[2]
def main():
    request=json.loads(sys.stdin.read() or "{}")
    if request.get("operation")=="backup":
        stamp=now_kst_iso()[:19].replace("-","").replace(":","").replace("T","_")
        folder=ROOT/"harness/memory"/("persona_source_connection_before_"+stamp)
        folder.mkdir(exist_ok=False)
        result={}
        for relative in ("config.py","haness/mcp/tools/orchestrator_tools.py"):
            source=ROOT/relative;destination=folder/relative
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
            result[relative]=hashlib.sha256(source.read_bytes()).hexdigest()
        print(json.dumps({"backup":str(folder.relative_to(ROOT)),"sha256":result}));return
    from haness.mcp.tools.orchestrator_tools import run_sps_orchestrator
    payload=request["payload"]
    print(json.dumps(asyncio.run(run_sps_orchestrator(json.dumps(payload,ensure_ascii=False),
                                                   dry_run=bool(request.get("dry_run",True)))),ensure_ascii=False))
if __name__=="__main__":main()
