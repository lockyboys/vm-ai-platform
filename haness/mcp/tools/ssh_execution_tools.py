"""SPS SSH 실행: 중앙 등록 대상에 한해 해시·로그·GPU 조회와 장기 Python 작업을 수행합니다."""
from __future__ import annotations
import re
import shlex
import subprocess
import uuid
from pathlib import Path, PurePosixPath
import config as settings
from common.common_function import logger

# 원격에서 실행되는 고정 프로그램입니다. 사용자 입력은 argv로만 전달합니다.
# resolve()로 심볼릭 링크까지 확인하여 저장소 밖의 파일을 읽지 않습니다.
REMOTE_HELPER = r'''
import hashlib, json, os, signal, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
op, relative, job, seconds, arguments = sys.argv[2:7]
target = (root / relative).resolve()
target.relative_to(root / "FastAPI" / "LangGraph")
jobs = root / ".sps_ssh_jobs"
if jobs.is_symlink():
    raise ValueError("job directory cannot be a symlink")
folder = jobs / job if job else jobs
if op == "hash":
    print(json.dumps({"path": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}))
elif op == "log":
    with target.open("rb") as handle:
        handle.seek(0, 2)
        handle.seek(max(0, handle.tell() - 12000))
        print(handle.read().decode("utf-8", errors="replace"))
elif op == "gpu":
    for cmd in (["nvidia-smi"], ["ollama", "ps"]):
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        print(json.dumps({"command": cmd, "returncode": result.returncode,
                          "stdout": result.stdout[-12000:], "stderr": result.stderr[-2000:]}))
elif op == "run":
    # MCP接続とは独立した子プロセスを起動し、状態と結果を作業IDで照会します。
    folder.mkdir(parents=True, mode=0o700, exist_ok=False)
    runner = r"""
import json, os, signal, subprocess, sys
from pathlib import Path
folder, root, seconds, command = sys.argv[1:5]
folder = Path(folder)
(folder / "status.json").write_text(json.dumps({"state": "running"}))
env = os.environ.copy()
env["PYTHONPATH"] = root
env["OLLAMA_TIMEOUT"] = seconds
code = None
timed_out = False
try:
    with (folder / "output.log").open("ab") as output:
        process = subprocess.Popen(json.loads(command), cwd=root, env=env,
                                   stdout=output, stderr=output, start_new_session=True)
        try:
            code = process.wait(timeout=int(seconds))
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    result = {"state": "finished", "returncode": code, "timed_out": timed_out}
except Exception as error:
    result = {"state": "failed", "error": str(error)}
temp = folder / "status.tmp"
temp.write_text(json.dumps(result))
temp.replace(folder / "status.json")
"""
    command = [sys.executable, "-u", str(target)] + json.loads(arguments)
    # 起動失敗はdispatchログに残り、statusでmissingと区別できます。
    with (folder / "dispatch.log").open("ab") as output:
        child = subprocess.Popen([sys.executable, "-c", runner, str(folder), str(root),
                                  seconds, json.dumps(command)],
                                 stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                 start_new_session=True)
    print(json.dumps({"state": "submitted", "job_id": job, "pid": child.pid,
                      "log_path": str(folder / "output.log")}))
elif op == "status":
    if not folder.is_dir():
        raise FileNotFoundError("unknown job_id")
    state = folder / "status.json"
    result = json.loads(state.read_text()) if state.exists() else {"state": "starting"}
    log = folder / "output.log"
    if not log.exists():
        log = folder / "dispatch.log"
    if log.exists():
        with log.open("rb") as handle:
            handle.seek(0, 2)
            handle.seek(max(0, handle.tell() - 12000))
            result["output"] = handle.read().decode("utf-8", errors="replace")
    print(json.dumps(result))
'''

def _credentials_ready(profile):
    """키의 내용은 읽지 않고 서비스 계정이 지정 파일을 사용할 수 있는지만 확인합니다."""
    return all(Path(profile[name]).is_file() for name in ("identity_file", "known_hosts")
               if profile.get(name))

def _relative(path, operation):
    """절대 경로·상위 경로 이동과 허용하지 않은 파일 종류를 거부합니다."""
    part = PurePosixPath(path)
    if part.is_absolute() or ".." in part.parts or not str(part).startswith("FastAPI/LangGraph/"):
        raise ValueError("Only project-relative FastAPI/LangGraph paths are allowed")
    suffix = part.suffix.lower()
    if operation == "log":
        if suffix not in (".log", ".txt"):
            raise ValueError("Only .log/.txt files can be read")
    elif suffix != ".py":
        raise ValueError("Only Python source paths are allowed")
    return str(part)

def run_remote(*, path, ssh_target, ssh_operation="hash", argv=None, job_id="",
               dry_run=True, execute_confirmed=False, timeout_seconds=120):
    """승인된 대상만 연결합니다. run은 원격 작업 ID를 반환하고 status로 결과를 조회합니다."""
    profile = settings.SPS_SSH_TARGETS.get(ssh_target)
    if not isinstance(profile, dict):
        raise ValueError("Unknown SSH target; register it in root config.py")
    if ssh_operation not in ("hash", "log", "gpu", "run", "status"):
        raise ValueError("Unsupported SSH operation")
    relative = _relative(path, ssh_operation)
    host, user = profile["host"], profile["user"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", host) or not re.fullmatch(r"[a-z_][a-z0-9_-]*", user):
        raise ValueError("Invalid SSH host/user")
    port = int(profile.get("port", 22))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid SSH port")
    args = [] if argv is None else argv
    if not isinstance(args, list) or len(args) > 64 or any(
        not isinstance(arg, str) or len(arg) > 4096 or "\x00" in arg for arg in args
    ):
        raise ValueError("Invalid Python arguments")
    if ssh_operation == "status" and not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise ValueError("Invalid job_id")
    if ssh_operation == "run":
        job_id = uuid.uuid4().hex
    seconds = max(1, min(int(timeout_seconds), settings.SPS_SSH_JOB_TIMEOUT_SECONDS))
    remote = shlex.join([profile["python"], "-c", REMOTE_HELPER, profile["root"],
                         ssh_operation, relative, job_id, str(seconds), __import__("json").dumps(args)])
    command = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15",
               "-o", "ServerAliveCountMax=2", "-p", str(port)]
    if profile.get("identity_file"):
        command += ["-i", profile["identity_file"], "-o", "IdentitiesOnly=yes"]
    if profile.get("known_hosts"):
        command += ["-o", "UserKnownHostsFile=" + profile["known_hosts"]]
    command += [user + "@" + host, remote]
    plan = {"dry_run": dry_run, "executed": False, "ssh_target": ssh_target,
            "ssh_operation": ssh_operation, "job_id": job_id, "command": command,
            "remote_command": remote, "timeout_seconds": seconds,
            "credentials_ready": _credentials_ready(profile),
            "llm_call_allowed": ssh_operation == "run" and not dry_run and execute_confirmed,
            "approval_required": not dry_run and not execute_confirmed}
    if dry_run or not execute_confirmed:
        return plan
    if not plan["credentials_ready"]:
        raise ValueError("SSH credentials files missing; configure the MCP service account")
    # 키·출력·명령 전체는 로그에 남기지 않고 대상 별칭과 작업 종류만 기록합니다.
    logger.info("MCP SSH operation: target=%s operation=%s", ssh_target, ssh_operation)
    from harness.mcp.tools.execution_tools import _trim_output
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False,
                                timeout=settings.SPS_SSH_REQUEST_TIMEOUT_SECONDS)
        return {**plan, "executed": True, "returncode": result.returncode,
                "timed_out": False, "stdout": _trim_output(result.stdout),
                "stderr": _trim_output(result.stderr)}
    except subprocess.TimeoutExpired as error:
        def decode(value):
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
        return {**plan, "executed": True, "returncode": None, "timed_out": True,
                "stdout": _trim_output(decode(error.stdout)), "stderr": _trim_output(decode(error.stderr))}
    except OSError as error:
        return {**plan, "executed": False, "returncode": None, "timed_out": False,
                "stdout": "", "stderr": _trim_output(str(error))}
