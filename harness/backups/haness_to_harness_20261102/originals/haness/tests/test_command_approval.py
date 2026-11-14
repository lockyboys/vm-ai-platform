"""실행 도구 위험 명령 탐지·승인 테스트(2026-10-25 LuckyBoys: 승인 기능 + 무슨 명령어인지 반드시 표시).

- sudo/ssh/curl 등 subprocess 문자열, 파이썬 네트워크 모듈, shell=True, config 명령 키를 찾는다
- 연결 파일(FastAPI/LangGraph) → import한 haness/scripts 실제 소스까지 따라가 찾는다
- 주석·일반 문장의 단어는 잡지 않는다
- 실행 도구: 찾은 명령이 있으면 approved_commands가 정확히 같을 때만 실행, 결과에 항상 명령 표시
"""
from __future__ import annotations

from pathlib import Path

import pytest

from haness.mcp.tools import command_approval as ca
from harness.mcp.tools import execution_tools


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("line,command", [
    ('subprocess.run(["sudo", "-n", "systemctl", "restart", "x"])', "sudo"),
    ("subprocess.run(['ssh', 'host', 'ls'])", "ssh"),
    ('os.popen("curl -s https://example.com")', "curl"),
    ('cmd = ["wget", url]', "wget"),
    ("import requests", "python:requests"),
    ("from urllib.request import urlopen", "python:urllib.request"),
    ("import paramiko", "python:paramiko"),
    ('subprocess.run(cmd, shell=True)', "shell"),
    ('os.system(cmd)', "shell"),
])
def test_dangerous_usage_is_detected(tmp_path, line, command):
    source = _write(tmp_path, "a.py", line + "\n")
    assert command in ca.command_names(ca.scan(source, tmp_path))


@pytest.mark.parametrize("line", [
    "# sudo 로 재시작하지 않는다", 'msg = "please use curl later"', "requests_count = 3", "import urllib.parse",
])
def test_comments_and_plain_words_are_not_flagged(tmp_path, line):
    source = _write(tmp_path, "a.py", line + "\n")
    assert ca.scan(source, tmp_path) == []


def test_follows_project_imports_from_connector(tmp_path):
    connector = _write(tmp_path, "FastAPI/LangGraph/run_x.py", "from haness.scripts.real_x import main\n")
    _write(tmp_path, "haness/scripts/real_x.py", 'import subprocess\nsubprocess.run(["sudo", "-n", "reboot"])\n')
    found = ca.scan(connector, tmp_path)
    assert {"sudo"} <= set(ca.command_names(found))
    assert found[0]["file"] == "haness/scripts/real_x.py" and found[0]["line"] == 2


def test_config_command_key_is_detected(tmp_path, monkeypatch):
    monkeypatch.setattr(ca.config, "SPS_FAKE_FOR_TEST", {"runner": ["sudo", "-n", "systemd-run"]}, raising=False)
    source = _write(tmp_path, "a.py", 'cmd = list(config.SPS_FAKE_FOR_TEST["runner"])\n')
    assert "sudo(config.runner)" in ca.command_names(ca.scan(source, tmp_path))


@pytest.mark.parametrize("approved,ok", [(None, False), ([], False), (["sudo"], False),
                                         (["curl", "sudo"], True), (["sudo", "curl", "ssh"], False)])
def test_approval_must_match_exactly(approved, ok):
    found = [{"command": "sudo"}, {"command": "curl"}, {"command": "sudo"}]
    assert ca.approval_matches(found, approved) is ok


def test_no_commands_needs_no_approval():
    assert ca.approval_matches([], None) is True


# --- 실행 도구 연결 -------------------------------------------------------------
@pytest.fixture()
def tool_root(tmp_path, monkeypatch):
    """실행 도구가 임시 프로젝트를 보게 하고, 실제 프로세스는 띄우지 않는다."""
    monkeypatch.setattr(execution_tools, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(execution_tools, "EXECUTION_ROOT", tmp_path / "FastAPI/LangGraph")
    calls = []

    class Done:
        returncode, stdout, stderr = 0, "ok", ""

    monkeypatch.setattr(execution_tools.subprocess, "run", lambda *a, **k: calls.append(a) or Done())
    _write(tmp_path, "FastAPI/LangGraph/danger.py", 'import subprocess\nsubprocess.run(["sudo", "-n", "ls"])\n')
    _write(tmp_path, "FastAPI/LangGraph/safe.py", "print('hi')\n")
    return calls


def test_dry_run_shows_commands(tool_root):
    result = execution_tools.mcp_codex_apps_run_python_source("FastAPI/LangGraph/danger.py")
    assert result["approval_commands"] == ["sudo"] and result["commands_detected"][0]["line"] == 2
    assert tool_root == []


@pytest.mark.parametrize("approved", [None, [], ["ssh"]])
def test_unapproved_dangerous_file_is_not_executed(tool_root, approved):
    result = execution_tools.mcp_codex_apps_run_python_source(
        "FastAPI/LangGraph/danger.py", dry_run=False, execute_confirmed=True, approved_commands=approved)
    assert result["executed"] is False and result["approval_required"] is True
    assert result["approval_commands"] == ["sudo"] and tool_root == []


def test_approved_dangerous_file_runs_and_still_shows_commands(tool_root):
    result = execution_tools.mcp_codex_apps_run_python_source(
        "FastAPI/LangGraph/danger.py", dry_run=False, execute_confirmed=True, approved_commands=["sudo"])
    assert result["executed"] is True and result["approval_commands"] == ["sudo"] and len(tool_root) == 1


def test_safe_file_runs_without_command_approval(tool_root):
    result = execution_tools.mcp_codex_apps_run_python_source(
        "FastAPI/LangGraph/safe.py", dry_run=False, execute_confirmed=True)
    assert result["executed"] is True and result["approval_commands"] == []
