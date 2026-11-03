"""GPU 튜닝 전 VM 가동·현재 주소를 읽기 전용으로 확인한다."""
import json, subprocess
r=subprocess.run(["gcloud","compute","instances","list","--filter=name=turing-enigma-ai","--format=json(name,status,zone,networkInterfaces)"],capture_output=True,text=True,timeout=25)
print(json.dumps({"returncode":r.returncode,"stdout":r.stdout,"stderr":r.stderr[-1500:]}))
