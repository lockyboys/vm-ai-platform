"""명시 승인된 기존 보험 RAG 서비스의 부팅 자동 시작만 해제하고 결과를 검증한다."""
import json
import subprocess
import sys

SERVICE = "fastapi-insurance-rag.service"

def run(args):
    # 비밀번호 입력 없이 지정한 서비스에만 명령을 적용한다.
    return subprocess.run(args, capture_output=True, text=True, timeout=35)

if sys.stdin.read().strip() != "DISABLE fastapi-insurance-rag.service":
    print(json.dumps({"dry_run": True, "service": SERVICE, "action": "disable"}))
else:
    # disable은 서비스 파일을 보존하면서 부팅 대상의 자동 시작 링크를 제거한다.
    result = run(["sudo", "-n", "systemctl", "disable", SERVICE])
    if result.returncode:
        print(json.dumps({"disabled": False, "error": result.stderr.strip()}))
        raise SystemExit(1)
    enabled = run(["systemctl", "is-enabled", SERVICE]).stdout.strip()
    active = run(["systemctl", "is-active", SERVICE]).stdout.strip()
    verified = enabled == "disabled" and active == "inactive"
    print(json.dumps({"service": SERVICE, "enabled": enabled, "active": active, "verified": verified}))
    raise SystemExit(0 if verified else 1)
