"""미완료 소스 참조·그래프·Git 날짜를 읽기 전용으로 조사한다."""
import ast,json,re,subprocess,sys
from pathlib import Path
ROOT=Path("/data/vm_project");sys.path.insert(0,str(ROOT))
from common.common_function import now_kst_iso,write_json_atomic
def git(*args):
    p=subprocess.run(["git",*args],cwd=ROOT,capture_output=True,text=True,timeout=15)
    return p.stdout
e={"checked_at":now_kst_iso()}
raw=git("grep","-n","-E","pipeline_results|PIPELINE_RESULTS_PAYLOAD","--","*.py")
rows=[line for line in raw.splitlines() if not any(x in line for x in ("/backups/","BACKUP","_backup","harness/memory/"))]
e["old_name_references"]=[line[:260] for line in rows]
e["graphs"]={}
for name in ["multi_persona_agent_gemini.py","multi_persona_agent_Ollama_Gemma4_e4b.py"]:
    p=ROOT/"FastAPI/LangGraph/multi_persona"/name;tree=ast.parse(p.read_text())
    edges=[ast.unparse(n)[:220] for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ("add_edge","add_conditional_edges")]
    e["graphs"][name]={"edge_calls":edges,"python_loop_count":sum(isinstance(n,(ast.For,ast.While,ast.AsyncFor)) for n in ast.walk(tree))}
e["area_git_dates"]={}
for label,path in {"common":"common","engine":"engine","generator":"generator","api":"FastAPI","harness":"harness","services":"services"}.items():
    lines=git("log","--reverse","--format=%h %cI","--",path).splitlines()
    e["area_git_dates"][label]={"first_git_commit":lines[0] if lines else None,"last_git_commit":lines[-1] if lines else None,"actual_initial_development_date":"미확인"}
e["branch"]=git("branch","--show-current").strip()
e["upstream"]=git("for-each-ref","--format=%(upstream:short) %(upstream:track)","refs/heads/"+e["branch"]).strip()
e["remote_names"]=git("remote").splitlines()
text=(ROOT/"harness/mcp/sps_harness_server.py").read_text()
e["instruction_assignment"]=[line for line in text.splitlines() if line.startswith("INSTRUCTION_FILE")]
e["checkpoint_automation"]={"dated_filename_implemented":"current_{kst_now:%Y%m%d}.md" in text,"write_timestamp_implemented":"Checkpoint updated at:" in text,"scheduled_automatic_execution":"미확인"}
write_json_atomic(ROOT/"harness/memory/followup_source_assessment_20261025.json",e)
print(json.dumps({"old_name_reference_count":len(rows),"old_name_paths":sorted(set(x.split(":",1)[0] for x in rows)),
 "graphs":{k:{"edge_count":len(v["edge_calls"]),"python_loop_count":v["python_loop_count"]} for k,v in e["graphs"].items()},
 "area_git_dates":e["area_git_dates"],"branch":e["branch"],"upstream":e["upstream"],"remote_names":e["remote_names"],
 "instruction_assignment":e["instruction_assignment"],"checkpoint":e["checkpoint_automation"]},ensure_ascii=False))
