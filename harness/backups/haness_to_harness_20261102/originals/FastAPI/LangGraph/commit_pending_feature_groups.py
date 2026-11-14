"""검증된 기능별 staging을 구성하고 나머지 staging·작업 파일을 보존한다. 커밋은 MCP 도구가 수행한다."""
import ast, hashlib, json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path("/data/vm_project")
STATE=ROOT/"haness/backups/pending_feature_commits_20261025_0520"
def git(*args,input=None):
    return subprocess.run(["git",*args],cwd=ROOT,input=input,capture_output=True,check=True).stdout
def entries():
    return {p.split(b"\t",1)[1].decode():p.split(b"\t",1)[0].decode() for p in git("ls-files","--stage","-z").split(b"\0") if p}
def digest(paths):
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
def assignment_names(node):
    if isinstance(node,ast.Assign):
        return [t.id for t in node.targets if isinstance(t,ast.Name)]
    if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name):
        return [node.target.id]
    return []
def main():
    req=json.loads(sys.stdin.read() or "{}")
    action=req.get("action","plan")
    index=ROOT/git("rev-parse","--git-path","index").decode().strip()
    if action=="plan":
        groups=req["groups"]
        paths=list(dict.fromkeys([p for g in groups for p in g["paths"]]+["config.py"]))
        source=(ROOT/"config.py").read_text()
        original=git("show","HEAD:config.py").decode()
        old_names={n for node in ast.parse(original).body for n in assignment_names(node)}
        new_names={n for node in ast.parse(source).body for n in assignment_names(node)}-old_names
        planned={n for g in groups for n in g["config"]}
        if new_names!=planned: raise RuntimeError("Unclassified config names: "+str(new_names^planned))
        plan={"head":git("rev-parse","HEAD").decode().strip(),"groups":groups,"paths":paths,
              "index_sha256":hashlib.sha256(index.read_bytes()).hexdigest(),"files":digest(paths),
              "original_entries":entries(),"original_config":source,"new_names":sorted(new_names)}
        if STATE.exists(): raise RuntimeError("State backup exists")
        STATE.mkdir(parents=True)
        (STATE/"plan.json").write_text(json.dumps(plan),encoding="utf-8")
        shutil.copy2(index,STATE/"original.index")
        print(json.dumps({"head":plan["head"],"groups":len(groups),"files":len(paths),"config_names":sorted(new_names)}))
        return
    plan=json.loads((STATE/"plan.json").read_text())
    if digest(plan["paths"])!=plan["files"]: raise RuntimeError("Worktree changed since plan")
    if action=="prepare":
        number=req["number"]
        if number==0:
            if git("rev-parse","HEAD").decode().strip()!=plan["head"]:raise RuntimeError("HEAD changed")
            if hashlib.sha256(index.read_bytes()).hexdigest()!=plan["index_sha256"]:raise RuntimeError("Index changed")
            git("read-tree","HEAD")
        elif git("diff","--cached","--name-only").strip():
            raise RuntimeError("Index not empty after preceding commit")
        group=plan["groups"][number]
        git("add","--",*group["paths"])
        if group["config"]:
            enabled={n for g in plan["groups"][:number+1] for n in g["config"]}
            lines=plan["original_config"].splitlines(keepends=True)
            nodes=ast.parse(plan["original_config"]).body
            remove=set()
            for idx,node in enumerate(nodes):
                names=set(assignment_names(node))
                if names & set(plan["new_names"]) and not names & enabled:
                    start=node.lineno-1
                    floor=nodes[idx-1].end_lineno if idx else 0
                    while start>floor and (not lines[start-1].strip() or lines[start-1].lstrip().startswith("#")):
                        start-=1
                    remove.update(range(start,node.end_lineno))
            selected="".join(line for i,line in enumerate(lines) if i not in remove)
            if "SPS_SOURCE_PARTNER_MODEL_PROVIDER" not in enabled:
                selected=selected.replace("# PARTNER는 하나의 LangGraph 구현을 유지하고 이 설정으로 Gemini/Ollama만 선택합니다.",
                    "# Preserve the existing model default while honoring the configured Gemini model.")
            compile(selected,"config.py","exec")
            blob=git("hash-object","-w","--stdin",input=selected.encode()).decode().strip()
            git("update-index","--add","--cacheinfo","100644",blob,"config.py")
        git("diff","--cached","--check")
        expected=sorted(group["paths"]+(["config.py"] if group["config"] else []))
        actual=sorted(git("diff","--cached","--name-only").decode().splitlines())
        if actual!=expected:raise RuntimeError("Unexpected staged files: "+str(actual))
        print(json.dumps({"number":number,"name":group["name"],"expected_paths":expected,"diff_check_passed":True}))
    elif action=="restore":
        if git("diff","--cached","--name-only").strip():raise RuntimeError("Uncommitted group")
        committed=set(plan["paths"])
        shutil.copy2(STATE/"original.index",index)
        for p in committed:
            line=git("ls-tree","HEAD","--",p).decode().strip()
            meta,name=line.split("\t",1)
            mode,kind,blob=meta.split()
            git("update-index","--add","--cacheinfo",mode,blob,p)
        current=entries()
        preserved=all(current.get(p)==v for p,v in plan["original_entries"].items() if p not in committed)
        if not preserved:raise RuntimeError("Other staging mismatch")
        if git("show","HEAD:config.py").decode()!=plan["original_config"]:raise RuntimeError("Final config differs")
        evidence={"commits":git("log","--format=%h %s",plan["head"]+"..HEAD").decode().splitlines(),
                  "worktree_preserved":digest(plan["paths"])==plan["files"],"other_staging_preserved":preserved,
                  "remaining_tracked":git("diff","HEAD","--name-only").decode().splitlines(),"backup":str(STATE)}
        (STATE/"verification.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(evidence,ensure_ascii=False))
    else:raise RuntimeError("Unknown action")
if __name__=="__main__":
    main()
