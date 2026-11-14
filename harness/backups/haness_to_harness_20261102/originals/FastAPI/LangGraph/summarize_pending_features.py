"""기능별 커밋 분류용 요약. 파일 내용과 비밀값은 출력하지 않는다."""
import json,subprocess
from pathlib import Path
R=Path("/data/vm_project")
def g(*a):return subprocess.run(["git",*a],cwd=R,capture_output=True,text=True,check=True).stdout
for name in g("diff","HEAD","--name-only").splitlines():
    if name.startswith("harness/memory/"):continue
    d=g("diff","HEAD","--",name)
    added=[x[1:] for x in d.splitlines() if x.startswith("+") and not x.startswith("+++")]
    print(json.dumps({"path":name,"hunks":[x for x in d.splitlines() if x.startswith("@@")][:2],
    "imports":[x for x in added if x.startswith(("import ","from "))][:3]},ensure_ascii=False))
for name in g("ls-files","--others","--exclude-standard").splitlines():
    if name.endswith(".py") and name.startswith(("haness/","harness/","tests/","scripts/","FastAPI/LangGraph/multi_persona/")) and not any(x in name for x in ["BACKUP","backup","memory/","pytest-"]):
        lines=(R/name).read_text(errors="replace").splitlines()
        print(json.dumps({"new":name,"lines":len(lines),"imports":[x for x in lines if x.startswith(("from ","import "))][:4]},ensure_ascii=False))
