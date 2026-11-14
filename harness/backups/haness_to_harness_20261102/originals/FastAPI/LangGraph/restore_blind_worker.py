import subprocess
from pathlib import Path
root=Path("/data/vm_project")
p=root/"haness/apps/blind_review_20261027/blind_worker.py"
r=subprocess.run(["git","show","HEAD:haness/apps/blind_review_20261027/blind_worker.py"],cwd=root,capture_output=True,text=True,check=True)
p.write_text(r.stdout,encoding="utf-8")
print("restored",len(r.stdout.splitlines()),"lines")
