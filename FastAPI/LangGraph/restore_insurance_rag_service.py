"""사용 중인 기존 보험 RAG 서비스의 실행과 부팅 자동 시작을 복구한다."""
import json
import subprocess
import sys
import time
SERVICE = "fastapi-insurance-rag.service"

def run(args):
    # 지정된 서비스만 조작하며 인증 설정과 원본 소스는 변경하지 않는다.
    return subprocess.run(args, capture_output=True, text=True, timeout=40)

if sys.stdin.read().strip() != "RESTORE fastapi-insurance-rag.service":
    print(json.dumps({"dry_run":True,"service":SERVICE,"action":"enable --now"}))
else:
    result = run(["sudo","-n","systemctl","enable","--now",SERVICE])
    if result.returncode:
        print(json.dumps({"restored":False,"error":result.stderr.strip()}))
        raise SystemExit(1)
    # 기동 직후의 지연을 고려해 최대 30초 동안 상태와 8003 리스너를 확인한다.
    deadline = time.monotonic() + 30
    while True:
        active = run(["systemctl","is-active",SERVICE]).stdout.strip()
        enabled = run(["systemctl","is-enabled",SERVICE]).stdout.strip()
        listener = run(["ss","-H","-ltn","sport","=",":8003"])
        listening = listener.returncode == 0 and bool(listener.stdout.strip())
        verified = active == "active" and enabled == "enabled" and listening
        if verified or time.monotonic() >= deadline:
            break
        time.sleep(1)
    print(json.dumps({"service":SERVICE,"active":active,"enabled":enabled,
                      "port_8003_listening":listening,"verified":verified}))
    raise SystemExit(0 if verified else 1)
