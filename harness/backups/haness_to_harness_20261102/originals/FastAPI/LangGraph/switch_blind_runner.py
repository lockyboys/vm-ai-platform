from pathlib import Path
import shutil, py_compile, subprocess
root=Path('/data/vm_project')
server=root/'harness/mcp/sps_harness_server.py'
backup=server.with_name('sps_harness_server.py_BACKUP_20261029_교체전')
shutil.copy2(server,backup)
s=server.read_text(encoding='utf-8')
old='from haness.mcp.tools.blind_review_jobs import submit as submit_blind_review, status as blind_review_status'
new='from haness.mcp.tools.blind_review_jobs_v2 import submit as submit_blind_review, status as blind_review_status'
if old not in s: raise SystemExit('old import not found')
server.write_text(s.replace(old,new,1),encoding='utf-8')
py_compile.compile(str(server),doraise=True)
print('patched',backup.name)
