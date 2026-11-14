import base64,json,zlib
from pathlib import Path
p=Path('/data/vm_project/haness/apps/blind_review_judge_20261027/private_judge.b64')
raw=''.join(p.read_text().split())
data=json.loads(zlib.decompress(base64.b64decode(raw)))
print(json.dumps({'keys':list(data.keys()),'partial_grades':data.get('partial_grades')},ensure_ascii=False))
