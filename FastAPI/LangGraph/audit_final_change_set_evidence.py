"""최종 변경 세트의 저장 증빙·현재 해시·스킬 패키지를 읽기 전용으로 대조한다."""
import collections,datetime,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path("/data/vm_project");sys.path.insert(0,str(ROOT))
from common.common_function import write_json_atomic
from FastAPI.LangGraph.skill_package_quick_validate import validate_skill
TARGETS=["config.py","haness/mcp/agents/source_partner_agent.py","haness/mcp/tools/change_set_graph.py",
"harness/mcp/tools/git_mutation_tools.py","tests/harness/mcp/test_source_partner_agent.py",
"tests/harness/mcp/test_sps_change_set_tool.py","tests/harness/mcp/test_mutation_tool_extensions.py"]
def git(*args):
    p=subprocess.run(["git",*args],cwd=ROOT,capture_output=True,text=True,timeout=20)
    return {"returncode":p.returncode,"stdout":p.stdout.strip()}
def main():
    evidence={"checked_at":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
              "scope":"PARTNER provider/model + same-graph stage_patch_groups + skill package; no SOURCE_AUDIT mutation",
              "evidence_files":{},"targets":{}}
    hashes={}
    for relative in ["harness/memory/change_set_evidence_fix_20261025.json","harness/memory/regression_verification_20261025.json",
                     "haness/backups/pending_feature_commits_20261025_0520/verification.json",
                     "haness/backups/git_feature_commits_20261025_0500/state.json"]:
        p=ROOT/relative
        summary={"exists":p.is_file()}
        if not p.is_file():evidence["evidence_files"][relative]=summary;continue
        raw=p.read_bytes();summary["sha256"]=hashlib.sha256(raw).hexdigest()
        doc=json.loads(raw);summary["top_keys"]=list(doc.keys()) if isinstance(doc,dict) else []
        facts=[];tests=[]
        def walk(obj,path="",depth=0):
            if depth>15:return
            if isinstance(obj,dict):
                if isinstance(obj.get("results"),list) and any(isinstance(x,dict) and "status" in x for x in obj["results"]):
                    counts=collections.Counter(x.get("status") for x in obj["results"] if isinstance(x,dict))
                    tests.append({"path":path,"counts":dict(counts),"exit_code":obj.get("exit_code")})
                for k,v in obj.items():
                    where=path+"."+k
                    if k in ("after_sha256","file_hashes","source_hashes","sha256") and isinstance(v,dict):
                        for name,value in v.items():
                            if isinstance(value,str) and re.fullmatch("[0-9a-f]{64}",value):hashes.setdefault(name,[]).append({"file":relative,"at":where,"hash":value})
                    if k in ("counts","exit_code","reload","reload_required","reload_decision","historical_compliance","existing_service_8003","diagnostic_limitation","verification","all_tests","command","test_paths","verified","original_state_preserved"):
                        if isinstance(v,(str,int,bool)) or k in ("counts","command","test_paths"):
                            facts.append({"key":where,"value":v if not isinstance(v,str) else v[:350]})
                    if isinstance(v,str) and k=="text" and v.lstrip().startswith(("{","[")):
                        try:walk(json.loads(v),where+".json",depth+1)
                        except (ValueError,TypeError):pass
                    elif isinstance(v,(dict,list)):walk(v,where,depth+1)
            elif isinstance(obj,list):
                if len(obj)>100 and all(isinstance(x,dict) and "node_id" in x for x in obj):return
                for i,v in enumerate(obj):walk(v,path+"["+str(i)+"]",depth+1)
        walk(doc);summary["facts"]=facts[:40];summary["test_summaries"]=tests
        evidence["evidence_files"][relative]=summary
    for name in TARGETS:
        p=ROOT/name
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        records=hashes.get(name,[])
        evidence["targets"][name]={"sha256":h,"saved_hash_records":[{**r,"matches":r["hash"]==h} for r in records],
            "worktree_vs_head_clean":git("diff","--quiet","HEAD","--",name)["returncode"]==0,
            "index_vs_head_clean":git("diff","--cached","--quiet","HEAD","--",name)["returncode"]==0,
            "latest_commit":git("log","-1","--format=%h %cI %s","--",name)["stdout"]}
    package=ROOT/"outputs/sps-orchestrator";skill=package/"SKILL.md"
    valid,message=validate_skill(package)
    links=[]
    if skill.is_file():
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)",skill.read_text()):
            if not re.match(r"[a-z]+://",target):
                links.append({"target":target,"exists":(package/target).is_file()})
    evidence["skill_package"]={"path":str(package),"format_valid":valid,"validator_message":message,
        "required_contract_exists":(package/"references/mcp-change-set-contract.md").is_file(),
        "declared_reference_links":links,"agents_yaml_exists":(package/"agents/openai.yaml").is_file(),
        "reference_files":[str(p.relative_to(package)) for p in sorted((package/"references").glob("*")) if p.is_file()],
        "mcp_contract_mentioned":("mcp-change-set-contract" in skill.read_text()) if skill.is_file() else False}
    evidence["head"]=git("rev-parse","HEAD")["stdout"]
    path=ROOT/"harness/memory/final_change_set_evidence_audit_20261025.json"
    write_json_atomic(path,evidence)
    print(json.dumps(evidence,ensure_ascii=False))
if __name__=="__main__":main()
