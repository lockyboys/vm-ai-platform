import json
from pathlib import Path
for provider in ('gemini','ollama'):
 p=Path('/data/vm_project/haness/apps/blind_review_20261027/results')/provider
 rows=[]
 for f in sorted(p.glob('*.json')):
  if f.name=='summary.json': continue
  try:
   x=json.loads(f.read_text())
   rows.append({'id':x.get('id'),'success':x.get('success'),'response_chars':len(x.get('response','')),'truncated':x.get('truncated')})
  except Exception: pass
 print(provider,json.dumps({'count':len(rows),'success':sum(r['success'] is True for r in rows),'truncated':sum(r['truncated'] is True for r in rows),'sample':rows[:2]},ensure_ascii=False))
