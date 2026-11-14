"""이미 진단이 허용된 두 서비스의 기동 시각과 관련 소스 수정 시각을 비교한다. 재기동하지 않는다."""
import datetime,json,os,subprocess,sys
from pathlib import Path
ROOT=Path("/data/vm_project");sys.path.insert(0,str(ROOT))
from common.common_function import now_kst_iso,write_json_atomic
KST=datetime.timezone(datetime.timedelta(hours=9))
bindings={"sps-harness.service":["haness/mcp/tools/change_set_graph.py","haness/mcp/agents/source_partner_agent.py","harness/mcp/tools/git_mutation_tools.py"],
"sps-gemini-agent.service":["FastAPI/LangGraph/gemini/sps_gemini_agent.py"]}
result={"checked_at":now_kst_iso(),"services":{}}
for service,files in bindings.items():
    p=subprocess.run(["systemctl","show",service,"--property=ActiveState,MainPID,ExecMainStartTimestamp"],capture_output=True,text=True,timeout=10,check=True,env={**os.environ,"LC_ALL":"C"})
    values=dict(line.split("=",1) for line in p.stdout.splitlines() if "=" in line)
    raw=values["ExecMainStartTimestamp"]
    parts=raw.split()
    zone=KST if parts[-1]=="KST" else datetime.timezone.utc if parts[-1]=="UTC" else None
    started=datetime.datetime.strptime(" ".join(parts[1:3]),"%Y-%m-%d %H:%M:%S").replace(tzinfo=zone) if zone else None
    checks=[]
    for f in files:
        modified=datetime.datetime.fromtimestamp((ROOT/f).stat().st_mtime,KST)
        checks.append({"path":f,"file_modified_kst":modified.isoformat(),"process_started_after_file":started is not None and started>=modified})
    result["services"][service]={"active":values["ActiveState"],"pid":values["MainPID"],"started":raw,"file_checks":checks}
write_json_atomic(ROOT/"harness/memory/final_reload_evidence_audit_20261025.json",result)
print(json.dumps(result,ensure_ascii=False))
