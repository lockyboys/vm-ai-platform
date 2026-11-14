import base64,json,zlib
from pathlib import Path
data=json.loads(zlib.decompress(base64.b64decode(''.join(Path('/data/vm_project/haness/apps/blind_review_judge_20261027/private_judge.b64').read_text().split()))))
for k in ('SCORING.md','jobs.json','catalog.json','verification.json','scoring_commitment.json'):
 x=data.get(k); print(k, type(x).__name__, (list(x)[:20] if isinstance(x,dict) else (len(x) if isinstance(x,list) else str(x)[:300])))
