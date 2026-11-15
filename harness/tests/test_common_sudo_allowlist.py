"""허용 목록 sudo 실행 공통 함수 검증 (2026-11-15, LuckyBoys 요청: "sudo 실행하는 도구 만들자").

결정(LuckyBoys 선택)
- 새 MCP 도구는 만들지 않는다. 기존 mcp_codex_apps_run_python_source의 위험 명령 승인(approval_commands)을 쓰고,
  실제 실행은 common.common_function.run_allowed_sudo 가 맡는다.
- config.SUDO_ALLOWED_COMMANDS 허용 목록에 있는 명령·인자만 실행한다. 목록 밖은 거부.
기대
- 허용된 명령은 dry-run이면 계획만, 실행이면 ["sudo", "-n", ...] 리스트로(셸 없이) 실행한다.
- 잘못된 입력(목록 밖 명령, 허용 안 된 인자, 셸 특수문자, 빈 값, 문자열 하나)은 ValueError.
실제 sudo는 실행하지 않는다(subprocess.run 대역).
"""
from types import SimpleNamespace

import pytest

import config as project_config
# 2026-11-15: sudo 함수는 common/sudo_runner.py로 옮겼다(common_function import만으로 sudo 승인을 요구하던 부작용 제거).
from common import sudo_runner as cf

# 실제 config 값(아래 autouse 대역으로 바뀌기 전에 잡아 둔다). 위험 명령이 빠졌는지 검사할 때 쓴다.
REAL_ALLOWED = getattr(project_config, "SUDO_ALLOWED_COMMANDS", None)

ALLOWED = {
    ("apt-get", "install", "-y"): ("libcups2", "libcups2t64"),
    ("systemctl", "restart"): ("sps-harness.service",),
    ("systemctl", "daemon-reload"): (),   # 빈 값 = 뒤에 인자를 붙일 수 없음
}


@pytest.fixture(autouse=True)
def allowlist(monkeypatch):
    """테스트용 허용 목록으로 바꾼다(실제 config 값과 무관하게 검사)."""
    monkeypatch.setattr(project_config, "SUDO_ALLOWED_COMMANDS", ALLOWED)
    monkeypatch.setattr(project_config, "SUDO_TIMEOUT_SECONDS", 30)


def test_reproduce_allowed_install_dry_run_plans_only(monkeypatch):
    """재현: libcups 설치를 dry-run하면 실행하지 않고 실제로 돌릴 명령만 보여 준다."""
    called = []
    monkeypatch.setattr(cf.subprocess, "run", lambda *a, **k: called.append(a))
    plan = cf.run_allowed_sudo(["apt-get", "install", "-y", "libcups2t64"], dry_run=True)
    assert plan["dry_run"] is True and plan["command"] == ["sudo", "-n", "apt-get", "install", "-y", "libcups2t64"]
    assert called == []


def test_allowed_command_executes_as_list_without_shell(monkeypatch):
    """실행: 셸 없이 리스트로 sudo -n 을 부르고 결과(종료 코드·출력 끝)를 돌려준다."""
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"], seen["kwargs"] = command, kwargs
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(cf.subprocess, "run", fake_run)
    result = cf.run_allowed_sudo(["systemctl", "restart", "sps-harness.service"], dry_run=False)
    assert seen["command"] == ["sudo", "-n", "systemctl", "restart", "sps-harness.service"]
    assert seen["kwargs"].get("shell") in (None, False) and seen["kwargs"]["timeout"] == 30
    assert result["returncode"] == 0 and result["stdout_tail"] == "ok\n"


@pytest.mark.parametrize("bad", [
    ["rm", "-rf", "/"],                                   # 목록 밖 명령
    ["apt-get", "install", "-y", "nginx"],                # 허용 안 된 패키지
    ["apt-get", "install", "-y"],                         # 대상 인자 없음
    ["apt-get", "remove", "-y", "libcups2"],              # 허용 안 된 동작
    ["systemctl", "restart", "sps-harness.service;id"],   # 셸 특수문자
    ["apt-get", "install", "-y", "libcups2", "--allow-downgrades"],  # 허용 안 된 추가 인자
    [],                                                   # 빈 목록
    ["", "install"],                                      # 빈 값
    "apt-get install -y libcups2",                        # 리스트가 아닌 문자열(셸 해석 위험)
    None,
])
def test_rejects_bad_input(bad, monkeypatch):
    """잘못된 입력은 sudo를 부르기 전에 ValueError로 멈춘다."""
    monkeypatch.setattr(cf.subprocess, "run", lambda *a, **k: pytest.fail("sudo must not run"))
    with pytest.raises(ValueError):
        cf.run_allowed_sudo(bad, dry_run=False)


def test_timeout_is_reported_not_raised(monkeypatch):
    """시간 초과는 예외 대신 결과(timed_out=True)로 보고한다."""
    def fake_run(command, **kwargs):
        raise cf.subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(cf.subprocess, "run", fake_run)
    result = cf.run_allowed_sudo(["systemctl", "restart", "sps-harness.service"], dry_run=False)
    assert result["timed_out"] is True and result["returncode"] is None


def test_no_argument_command_allowed_only_without_arguments(monkeypatch):
    """값이 빈 명령(daemon-reload)은 인자 없이만 허용, 뒤에 무엇을 붙이면 거부."""
    monkeypatch.setattr(cf.subprocess, "run", lambda *a, **k: pytest.fail("sudo must not run"))
    assert cf.run_allowed_sudo(["systemctl", "daemon-reload"])["command"] == ["sudo", "-n", "systemctl", "daemon-reload"]
    with pytest.raises(ValueError):
        cf.run_allowed_sudo(["systemctl", "daemon-reload", "x"], dry_run=False)


@pytest.mark.parametrize("dangerous", [
    ["rm", "-rf", "/tmp/x"],
    ["kill", "-TERM", "1"],
    ["python3", "-c", "print"],
    ["cat", "/etc/sps-harness/secrets.env"],
])
def test_real_config_excludes_anything_commands(dangerous, monkeypatch):
    """LuckyBoys 결정(2026-11-15): rm -rf·kill·python3 -c·cat(보호 파일)은 실제 허용 목록에서 빠져 있어야 한다."""
    assert REAL_ALLOWED, "config.SUDO_ALLOWED_COMMANDS가 없습니다"
    assert not any(prefix[0] == dangerous[0] for prefix in REAL_ALLOWED)
    monkeypatch.setattr(project_config, "SUDO_ALLOWED_COMMANDS", REAL_ALLOWED)
    monkeypatch.setattr(cf.subprocess, "run", lambda *a, **k: pytest.fail("sudo must not run"))
    with pytest.raises(ValueError):
        cf.run_allowed_sudo(dangerous, dry_run=False)
