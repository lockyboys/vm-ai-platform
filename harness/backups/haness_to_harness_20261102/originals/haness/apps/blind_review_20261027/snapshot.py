"""Read-only progress/export helper; never calls either model."""
import json,base64,zlib
from pathlib import Path
ROOT=Path("/data/vm_project/haness/apps/blind_review_20261027")
result={}
for provider in ("gemini","ollama"):
 p=ROOT/"results"/provider
 if (p/"summary.json").exists():
  summary=json.loads((p/"summary.json").read_text())
  runs=[json.loads(f.read_text()) for f in sorted(p.glob("*.json")) if f.name!="summary.json"]
  result[provider]={"summary":summary,"results":runs}
  print(json.dumps({"provider":provider,"status":summary["status"],"completed":summary["completed"],"total":summary["total"],"model":summary.get("model"),"last":summary.get("runs",[])[-1:]},ensure_ascii=False))
payload=base64.b64encode(zlib.compress(json.dumps(result,ensure_ascii=False).encode())).decode()
(ROOT/"snapshot.b64").write_text("\n".join(payload[i:i+2000] for i in range(0,len(payload),2000)))
print(json.dumps({"export":"haness/apps/blind_review_20261027/snapshot.b64","chars":len(payload)}))
