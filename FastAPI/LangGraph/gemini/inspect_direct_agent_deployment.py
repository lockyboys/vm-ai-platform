"""Inspect direct Agent API deployment prerequisites; never print credentials."""
from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path("/data/vm_project")

def main():
    # Read-only checks: gcloud availability, current config, restart capability and live schema.
    gcloud = shutil.which("gcloud")
    result = {"gcloud_available": bool(gcloud)}
    if gcloud:
        command = [gcloud, "api-gateway", "gateways", "describe", "sps-mcp-gateway",
                   "--location=asia-northeast1", "--project=gen-lang-client-0968716109",
                   "--format=json(state,apiConfig)"]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
        result["gateway_returncode"] = completed.returncode
        if completed.returncode == 0:
            result["gateway"] = json.loads(completed.stdout)
        else:
            # Error text can contain account details; return only a bounded diagnostic.
            result["gateway_error"] = completed.stderr[-1500:]
    permission = subprocess.run(["sudo", "-n", "-l"], capture_output=True, text=True, timeout=5)
    result["sudo_noninteractive_available"] = permission.returncode == 0
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
