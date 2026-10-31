import json
from pathlib import Path
p=Path('/data/vm_project/haness/apps/blind_review_20261027/results/ollama')
rows=[]
for f in p.glob('*.json'):
    if f.name=='summary.json': continue
    try:
        x=json.loads(f.read_text())
        if isinstance(x,dict) and 'id' in x: rows.append(x)
    except Exception: pass
print(json.dumps({'files':len(rows),'success':sum(x.get('success') is True for x in rows),'failure':sum(x.get('success') is False for x in rows),'unknown':sum('success' not in x for x in rows),'ids':len({x.get('id') for x in rows})},ensure_ascii=False))
