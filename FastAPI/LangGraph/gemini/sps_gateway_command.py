"""Send commands to the deployed Gemini HTTP API without registering another MCP tool."""
import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path("/data/vm_project")
sys.path.insert(0, str(ROOT))


def validate_request(payload):
    # Fail before process creation/authentication on malformed, blank or oversized commands.
    if not isinstance(payload, dict):
        raise ValueError("Request must be an object")
    prompt = payload.get("user_input")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20000:
        raise ValueError("user_input must be nonblank text of at most 20000 characters")
    return prompt


def main():
    payload = json.loads(sys.stdin.read())
    prompt = validate_request(payload)
    from config import (SPS_AGENT_GATEWAY_URL, SPS_AGENT_GATEWAY_SUBJECT_ID,
                        SPS_AGENT_GATEWAY_TIMEOUT_SECONDS)
    endpoint = SPS_AGENT_GATEWAY_URL.rstrip("/") + "/agent/chat"
    if not payload.get("apply", False):
        print(json.dumps({"dry_run": True, "endpoint": endpoint, "user_input": prompt}, ensure_ascii=False))
        return
    if "--worker" not in sys.argv:
        # Detach before calling Gateway: its Agent may call back to the same MCP process.
        evidence = "harness/memory/gateway_command_" + uuid4().hex + ".json"
        target = ROOT / evidence
        target.write_text('{"state":"running"}', encoding="utf-8")
        payload["evidence"] = evidence
        child = subprocess.Popen([sys.executable, __file__, "--worker"], stdin=subprocess.PIPE,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 text=True, start_new_session=True, cwd=ROOT)
        child.stdin.write(json.dumps(payload, ensure_ascii=False))
        child.stdin.close()
        print(json.dumps({"submitted": True, "pid": child.pid, "evidence": evidence}))
        return
    import httpx
    from common.auth import CommonAuth
    from common.common_function import logger
    # Only CommonAuth sees protected signing settings. Never log bearer or auth headers.
    try:
        bearer = CommonAuth().issue_access_token(SPS_AGENT_GATEWAY_SUBJECT_ID)
        with httpx.Client(trust_env=False, timeout=SPS_AGENT_GATEWAY_TIMEOUT_SECONDS) as client:
            response = client.post(endpoint, json={"user_input": prompt},
                                   headers={"Authorization": "Bearer " + bearer})
        response.raise_for_status()
        result = response.json().get("result")
        if not isinstance(result, str) or not result.strip():
            raise ValueError("Agent response has no text result")
        receipt = {"state": "completed", "http_status": response.status_code, "result": result}
    except Exception as error:
        logger.error("Gateway command failed: %s", type(error).__name__)
        receipt = {"state": "failed", "error_type": type(error).__name__}
    # Atomic final receipt avoids exposing partial output to a polling reader.
    target = ROOT / payload["evidence"]
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)


if __name__ == "__main__":
    main()
