"""미커밋 코드의 기능 분류 자료를 읽기 전용으로 수집한다. 비밀·백업·로그는 읽지 않는다."""
import json,re,subprocess
from pathlib import Path
ROOT=Path("/data/vm_project")
def git(*args):
    return subprocess.run(["git",*args],cwd=ROOT,capture_output=True,text=True,check=True).stdout
tracked=git("diff","HEAD","--name-only").splitlines()
for name in tracked:
    if name.startswith("harness/memory/"):continue
    diff=git("diff","HEAD","--",name)
    added=[x[1:] for x in diff.splitlines() if x.startswith("+") and not x.startswith("+++")]
    print(json.dumps({"path":name,"hunks":[x for x in diff.splitlines() if x.startswith("@@")],
        "definitions":[x.strip() for x in added if re.match(r"\s*(?:async )?def |\s*class |import |from ",x)],
        "added_lines":len(added)},ensure_ascii=False))
new=git("ls-files","--others","--exclude-standard").splitlines()
for name in new:
    if not name.endswith(".py") or re.search(r"BACKUP|backup|memory/|pytest-|snapshots",name):continue
    if not name.startswith(("haness/","harness/","tests/","scripts/","FastAPI/LangGraph/multi_persona/")):continue
    p=ROOT/name
    lines=p.read_text(errors="replace").splitlines()
    print(json.dumps({"new":name,"lines":len(lines),"header":lines[:2],
        "imports":[x for x in lines if x.startswith(("from ","import "))],
        "definitions":[x for x in lines if x.startswith(("def ","class "))]},ensure_ascii=False))
