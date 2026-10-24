"""Deploy the existing Agent HTTP endpoint; keep the previous gateway config for rollback."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/data/vm_project")
PROJECT = "gen-lang-client-0968716109"
CONFIG = "sps-mcp-cfg-v22-20261019-2026"
RECEIPT = ROOT / "harness/memory/direct_agent_api_deployment_20261019.json"

def run(args, timeout=40):
    # Never invoke a shell or emit credentials; propagate CLI failure as a failed step.
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(p.stderr[-1800:])
    return p.stdout

def gcloud(*args):
    return run([shutil.which("gcloud") or "gcloud", *args, "--project=" + PROJECT])

def main():
    # Default to a read-only status check. Mutations require an explicit stdin action.
    action = json.loads(sys.stdin.read() or "{}").get("action", "status")
    if action == "create":
        previous = json.loads(gcloud("api-gateway", "gateways", "describe", "sps-mcp-gateway",
                                     "--location=asia-northeast1", "--format=json(state,apiConfig)"))
        RECEIPT.write_text(json.dumps({"previous_gateway": previous, "new_config": CONFIG}, indent=2))
        print(gcloud("api-gateway", "api-configs", "create", CONFIG, "--api=sps-mcp-api",
                     "--openapi-spec=" + str(ROOT / "openapi-spec.yaml"),
                     "--display-name=SPS Direct Gemini Agent API", "--async", "--format=json"))
    elif action == "status":
        print(gcloud("api-gateway", "api-configs", "describe", CONFIG, "--api=sps-mcp-api",
                     "--format=json(state,name)"))
        print(gcloud("api-gateway", "gateways", "describe", "sps-mcp-gateway",
                     "--location=asia-northeast1", "--format=json(state,apiConfig)"))
    elif action == "operations":
        # Inspect pending cloud operations to distinguish rollout progress from failure.
        print(gcloud("api-gateway", "operations", "list", "--location=asia-northeast1",
                     "--filter=NOT done:true", "--limit=3", "--format=json(name,done,error,metadata)"))
    elif action == "update":
        # The immutable new config must be ready before changing the live gateway.
        state = json.loads(gcloud("api-gateway", "api-configs", "describe", CONFIG,
                                 "--api=sps-mcp-api", "--format=json(state)"))
        if state.get("state") != "ACTIVE":
            raise RuntimeError("New API config is not ACTIVE")
        print(gcloud("api-gateway", "gateways", "update", "sps-mcp-gateway",
                     "--location=asia-northeast1", "--api=sps-mcp-api",
                     "--api-config=" + CONFIG, "--async", "--format=json"))
    elif action == "restart-agent":
        print(run(["sudo", "-n", "systemctl", "restart", "sps-gemini-agent.service"]))
        print(run(["systemctl", "is-active", "sps-gemini-agent.service"]))
    elif action == "restart-harness":
        # Queue the restart so the MCP process can return this receipt before stopping.
        print(run(["sudo", "-n", "systemctl", "restart", "--no-block", "sps-harness.service"]))
        print("Harness restart queued; verify status and tools/list after reconnection.")
    else:
        raise ValueError("Unknown deployment action")

if __name__ == "__main__":
    main()
