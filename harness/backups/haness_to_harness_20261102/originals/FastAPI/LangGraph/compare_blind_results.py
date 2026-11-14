import json,statistics
from pathlib import Path
for provider in ('gemini','ollama'):
 p=Path('/data/vm_project/haness/apps/blind_review_20261027/results')/provider
 rows=[]
 for f in p.glob('*.json'):
  if f.name=='summary.json': continue
  try:
   x=json.loads(f.read_text())
   if isinstance(x,dict) and 'id' in x: rows.append(x)
  except Exception: pass
 t=[x.get('elapsed_seconds') for x in rows if isinstance(x.get('elapsed_seconds'),(int,float))]
 print(json.dumps({'provider':provider,'files':len(rows),'success':sum(x.get('success') is True for x in rows),'failure':sum(x.get('success') is False for x in rows),'ids':len({x.get('id') for x in rows}),'avg_sec':round(statistics.mean(t),3) if t else None,'median_sec':round(statistics.median(t),3) if t else None,'total_sec':round(sum(t),3) if t else None},ensure_ascii=False))
