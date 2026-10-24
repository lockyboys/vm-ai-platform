"""사용자가 지정한 기존 보험 RAG 서비스만 중지하고 리스너 종료를 확인한다."""
import json
import subprocess
import sys
SERVICE = "fastapi-insurance-rag.service"
def run(args):
    # 비대화식 sudo로만 실행하며 비밀번호를 수집하거나 다른 서비스를 변경하지 않는다.
    return subprocess.run(args, capture_output=True, text=True, timeout=40)
if sys.stdin.read().strip() != "STOP fastapi-insurance-rag.service":
    print(json.dumps({"dry_run": True, "service": SERVICE, "action": "stop",
                      "disable": False, "verification": ["is-active", "8003 listener"]}))
else:
    result = run(["sudo", "-n", "systemctl", "stop", SERVICE])
    if result.returncode:
        print(json.dumps({"stopped":False,"returncode":result.returncode,"error":result.stderr.strip()}))
        raise SystemExit(1)
    state = run(["systemctl", "is-active", SERVICE]).stdout.strip()
    listener = run(["ss", "-H", "-ltn", "sport", "=", ":8003"])
    verified = state == "inactive" and listener.returncode == 0 and not listener.stdout.strip()
    print(json.dumps({"service":SERVICE,"state":state,"port_8003_listening":bool(listener.stdout.strip()),
                      "verified":verified,"disabled":False}))
    raise SystemExit(0 if verified else 1)
