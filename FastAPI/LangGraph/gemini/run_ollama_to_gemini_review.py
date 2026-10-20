"""Launch the exact Ollama-to-Gemini review in an independent systemd unit."""
from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path("/data/vm_project")
OLLAMA = ROOT / "FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py"
TARGET = ROOT / "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py"
REPORT = ROOT / "harness/memory/ollama_to_gemini_review_20261020.json"

def worker() -> None:
    command = [sys.executable, str(OLLAMA), "--source-path", str(TARGET)]
    started = time.time()
    try:
        completed = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True,
                                   timeout=300, check=False)
        result = {"state": "completed", "command": command, "returncode": completed.returncode,
                  "timed_out": False, "success": completed.returncode == 0,
                  "elapsed_seconds": round(time.time() - started, 3),
                  "stdout": completed.stdout, "stderr": completed.stderr}
    except subprocess.TimeoutExpired as error:
        result = {"state": "timed_out", "command": command, "returncode": None,
                  "timed_out": True, "success": False,
                  "elapsed_seconds": round(time.time() - started, 3),
                  "stdout": error.stdout or "", "stderr": error.stderr or ""}
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

def main() -> None:
    unit = "sps-ollama-to-gemini-" + uuid4().hex
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    command = ["sudo", "-n", "systemd-run", "--collect", "--quiet", "--unit=" + unit,
               "-p", "User=jeaje", "-p", "WorkingDirectory=" + str(ROOT),
               "-p", "EnvironmentFile=" + str(ROOT / ".env"),
               "-p", "EnvironmentFile=/etc/sps-harness/secrets.env",
               "-p", "RuntimeMaxSec=310", "-p", "TimeoutStopSec=2",
               str(ROOT / "venv/bin/python"), "-u", __file__, "--worker"]
    REPORT.write_text(json.dumps({"state": "starting", "unit": unit,
                                  "command": [str(ROOT / "venv/bin/python"), str(OLLAMA),
                                              "--source-path", str(TARGET)]},
                                 ensure_ascii=False), encoding="utf-8")
    launched = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
    if launched.returncode:
        REPORT.write_text(json.dumps({"state": "launch_failed", "unit": unit,
                                      "stderr": launched.stderr}, ensure_ascii=False), encoding="utf-8")
        raise SystemExit(launched.returncode)
    print(json.dumps({"state": "running", "unit": unit,
                      "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False))

if __name__ == "__main__":
    if "--worker" in sys.argv:
        worker()
    else:
        main()
