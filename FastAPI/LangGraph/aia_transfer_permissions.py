"""추가전송_32개 폴더의 SFTP 읽기 권한을 확인하고 필요 시 보정한다."""
import json
import os
import stat
import sys
from pathlib import Path

folder=Path("/data/vm_project/outputs/insurance_docs/AIA/first_page_named/추가전송_32개")
opts=json.loads(sys.stdin.read() or "{}")
apply=opts.get("apply") is True
if not folder.is_dir() or folder.is_symlink():
    raise ValueError("대상 폴더 없음 또는 링크")
items=list(folder.iterdir())
if len(items)!=32 or any(not p.is_file() or p.is_symlink() or p.suffix.lower()!=".pdf" for p in items):
    raise ValueError("PDF 32개만 있는 폴더가 아님")
parents=[folder.parent,folder]
before=[{"path":str(p),"mode":oct(stat.S_IMODE(p.stat().st_mode))} for p in parents]
file_modes={}
for p in items:
    mode=stat.S_IMODE(p.stat().st_mode)
    file_modes[oct(mode)]=file_modes.get(oct(mode),0)+1
    if p.stat().st_uid != os.geteuid():
        raise ValueError("파일 소유권 오류")
if apply:
    if folder.stat().st_uid != os.geteuid():
        raise ValueError("폴더 소유권 오류")
    folder.chmod(0o755)
    for p in items:
        p.chmod(0o644)
after=[{"path":str(p),"mode":oct(stat.S_IMODE(p.stat().st_mode))} for p in parents]
remaining={}
for p in items:
    mode=stat.S_IMODE(p.stat().st_mode)
    remaining[oct(mode)]=remaining.get(oct(mode),0)+1
print(json.dumps({"apply":apply,"parent_and_folder_before":before,"file_modes_before":file_modes,
"parent_and_folder_after":after,"file_modes_after":remaining,"count":len(items),
"bytes":sum(p.stat().st_size for p in items)},ensure_ascii=False))
