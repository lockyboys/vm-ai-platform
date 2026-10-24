"""Read termination evidence for the requested transient source review only."""
import json
import subprocess
from harness.mcp.tools.execution_tools import _mask_secrets

unit = "sps-source-review-2a4f023ae0ca4a839142c3489c69ec36"
for args in [
    ["systemctl", "show", unit, "--property=Result,ExecMainStatus,ActiveState"],
    ["journalctl", "-u", unit, "--no-pager", "-n", "12", "-o", "short-iso"]]:
    # Read-only evidence; no environment file content or authentication token is printed.
    result = subprocess.run(args, capture_output=True, text=True, timeout=10)
    print(json.dumps({"operation": args[0], "returncode": result.returncode,
                      "stdout": _mask_secrets(result.stdout), "stderr": _mask_secrets(result.stderr)},
                     ensure_ascii=False))
