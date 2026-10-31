"""전체 회귀를 실행하고 원문·반환코드를 증빙 파일에 보존한다."""
import json, subprocess
from pathlib import Path
folder = Path("harness/memory/timeout_policy_20261026")
folder.mkdir(parents=True,exist_ok=True)
try:
    result = subprocess.run(["/data/vm_project/venv/bin/python","-m","pytest","tests/","haness/tests/","--import-mode=importlib","-q","--tb=short"],capture_output=True,text=True,timeout=110)
    data = {"exit_code":result.returncode,"stdout":result.stdout,"stderr":result.stderr}
except subprocess.TimeoutExpired as exc:
    def text(value):
        return value.decode(errors="replace") if isinstance(value,bytes) else value or ""
    data = {"exit_code":124,"timed_out":True,"stdout":text(exc.stdout),"stderr":text(exc.stderr)}
(folder/"full_regression.json").write_text(json.dumps(data,ensure_ascii=False,indent=2))
print(json.dumps({"exit_code":data["exit_code"],"stdout_tail":data["stdout"][-9000:],"stderr":data["stderr"][-1000:]},ensure_ascii=False))
