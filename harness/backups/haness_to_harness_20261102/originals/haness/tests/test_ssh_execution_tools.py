"""SSH 경계·dry-run·원격 장기 실행을 외부 접속 없이 검증합니다."""
import subprocess
from types import SimpleNamespace
import pytest
from haness.mcp.tools import ssh_execution_tools as ssh

@pytest.fixture
def target(monkeypatch):
    monkeypatch.setattr(ssh.settings, "SPS_SSH_TARGETS", {"gpu": {
        "host": "34.64.134.46", "user": "jeajea_park", "port": 22,
        "identity_file": "/tmp/test-key", "known_hosts": "/tmp/test-known-hosts",
        "root": "/data/vm_project", "python": "/data/vm_project/venv/bin/python",
    }})
    monkeypatch.setattr(ssh, "_credentials_ready", lambda profile: True)

def call(**kwargs):
    return ssh.run_remote(path="FastAPI/LangGraph/example.py", ssh_target="gpu", **kwargs)

def test_dry_run_never_connects(target, monkeypatch):
    monkeypatch.setattr(ssh.subprocess, "run", lambda *a, **k: pytest.fail("SSH started"))
    result = call()
    assert not result["executed"]
    assert "StrictHostKeyChecking=yes" in result["command"]
    assert result["ssh_operation"] == "hash"

@pytest.mark.parametrize("path", ["../secret.py", "/etc/passwd", "FastAPI/LangGraph/../secret.py"])
def test_invalid_paths_rejected(target, path):
    with pytest.raises(ValueError):
        ssh.run_remote(path=path, ssh_target="gpu")

def test_unknown_target_rejected(target):
    with pytest.raises(ValueError):
        ssh.run_remote(path="FastAPI/LangGraph/a.py", ssh_target="-oProxyCommand=bad")

def test_missing_credentials_blocks_execution(target, monkeypatch):
    monkeypatch.setattr(ssh, "_credentials_ready", lambda profile: False)
    with pytest.raises(ValueError, match="credentials"):
        call(dry_run=False, execute_confirmed=True)

def test_hash_execution_uses_short_ssh_timeout(target, monkeypatch):
    seen = {}
    def run(command, **kwargs):
        seen.update(command=command, **kwargs)
        return SimpleNamespace(returncode=0, stdout="abc source.py", stderr="")
    monkeypatch.setattr(ssh.subprocess, "run", run)
    result = call(dry_run=False, execute_confirmed=True)
    assert result["executed"] and result["returncode"] == 0
    assert seen["timeout"] <= 120
    assert seen.get("shell", False) is False

def test_long_model_job_detaches_and_quotes_arguments(target):
    result = call(ssh_operation="run", timeout_seconds=3000,
                  argv=["--source-path", "FastAPI/LangGraph/input.py"])
    assert result["job_id"]
    assert result["timeout_seconds"] == 3000
    assert "start_new_session=True" in result["remote_command"]
    assert "process.wait(timeout=int(seconds))" in result["remote_command"]
    assert "3000" in result["remote_command"]

def test_status_requires_generated_job_id(target):
    with pytest.raises(ValueError):
        call(ssh_operation="status", job_id="../other")

def test_approval_required(target, monkeypatch):
    monkeypatch.setattr(ssh.subprocess, "run", lambda *a, **k: pytest.fail("SSH started"))
    assert call(dry_run=False)["approval_required"]

def test_timeout_is_reported(target, monkeypatch):
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired("ssh", 120, output=b"partial")
    monkeypatch.setattr(ssh.subprocess, "run", run)
    result = call(dry_run=False, execute_confirmed=True)
    assert result["timed_out"]
    assert result["stdout"] == "partial"
