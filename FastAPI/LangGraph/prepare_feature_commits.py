"""승인된 두 기능만 커밋하기 위해 기존 index를 백업·복원한다. 작업 파일은 수정하지 않는다."""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
ROOT=Path("/data/vm_project")
STATE=ROOT/"haness/backups/git_feature_commits_20261025_0500"
AUTH=["FastAPI/LangGraph/fix_8003_service_auth.py","FastAPI/LangGraph/verify_8003_answer_generation.py",
      "tests/test_service_8003_auth_live.py","deployment/systemd/fastapi-insurance-rag.service.d/90-sps-auth.conf"]
CLI=["FastAPI/LangGraph/agent_cli.py","tests/test_agent_cli.py","config.py"]
def git(*args,input=None):
    return subprocess.run(["git",*args],cwd=ROOT,input=input,capture_output=True,check=True).stdout
def entries():
    return {p.split(b"\t",1)[1].decode():p.split(b"\t",1)[0].decode() for p in git("ls-files","--stage","-z").split(b"\0") if p}
def fingerprints():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in AUTH+CLI}
def main():
    request=json.loads(sys.stdin.read() or "{}")
    action=request.get("action","plan")
    index=ROOT/git("rev-parse","--git-path","index").decode().strip()
    if action=="plan":
        if STATE.exists(): raise RuntimeError("Backup exists")
        print(json.dumps({"head":git("rev-parse","HEAD").decode().strip(),"auth":AUTH,"cli":CLI,
                          "index_sha256":hashlib.sha256(index.read_bytes()).hexdigest(),"files":fingerprints()}))
        return
    if action=="prepare_auth":
        if STATE.exists(): raise RuntimeError("Backup exists")
        if git("rev-parse","HEAD").decode().strip()!=request["head"]: raise RuntimeError("HEAD changed")
        if hashlib.sha256(index.read_bytes()).hexdigest()!=request["index_sha256"]: raise RuntimeError("Index changed")
        if fingerprints()!=request["files"]: raise RuntimeError("Files changed")
        STATE.mkdir(parents=True)
        shutil.copy2(index,STATE/"original.index")
        state={"head":request["head"],"original_entries":entries(),"files":fingerprints()}
        (STATE/"state.json").write_text(json.dumps(state),encoding="utf-8")
        # read-tree는 index만 바꾼다. 백업한 다른 기능의 staging은 마지막에 되돌린다.
        git("read-tree","HEAD")
        git("add","--",*AUTH)
    elif action=="prepare_cli":
        state=json.loads((STATE/"state.json").read_text())
        if fingerprints()!=state["files"]: raise RuntimeError("Files changed")
        if git("diff","--cached","--name-only").strip(): raise RuntimeError("Index not empty")
        git("add","--",*CLI[:2])
        # 공통 config 전체가 아닌 CLI 설정 블록만 HEAD에 덧붙인 blob을 index에 넣는다.
        source=(ROOT/"config.py").read_text()
        marker="# 로컬 8003 API의 터미널 검증 설정."
        if source.count(marker)!=1: raise RuntimeError("CLI config boundary ambiguous")
        base=git("show","HEAD:config.py").decode()
        if "AGENT_CLI =" in base: raise RuntimeError("CLI config already committed")
        selected=base.rstrip()+"\n\n"+marker+source.split(marker,1)[1]
        compile(selected,"config.py","exec")
        blob=git("hash-object","-w","--stdin",input=selected.encode()).decode().strip()
        git("update-index","--add","--cacheinfo","100644",blob,"config.py")
    elif action=="restore":
        state=json.loads((STATE/"state.json").read_text())
        if fingerprints()!=state["files"]: raise RuntimeError("Worktree changed; manual restore required")
        if git("diff","--cached","--name-only").strip(): raise RuntimeError("Index not empty")
        # 커밋된 파일은 새 HEAD의 항목을 유지하고, 공통 config의 기존 staging blob은 그대로 보존한다.
        shutil.copy2(STATE/"original.index",index)
        for path in AUTH+CLI[:2]:
            line=git("ls-tree","HEAD","--",path).decode().strip()
            metadata,name=line.split("\t",1)
            mode,kind,blob=metadata.split()
            git("update-index","--add","--cacheinfo",mode,blob,path)
        current=entries()
        committed=set(AUTH+CLI[:2])
        original=state["original_entries"]
        preserved=all(current.get(p)==v for p,v in original.items() if p not in committed)
        if not preserved: raise RuntimeError("Other staging mismatch")
        print(json.dumps({"other_staging_preserved":preserved,"worktree_preserved":fingerprints()==state["files"],
                          "head":git("rev-parse","HEAD").decode().strip(),"backup":str(STATE)}))
        return
    else:
        raise RuntimeError("Unknown action")
    print(json.dumps({"staged_paths":git("diff","--cached","--name-only").decode().splitlines(),
                      "diff_check_passed":not bool(git("diff","--cached","--check").strip())}))
if __name__=="__main__":
    main()
