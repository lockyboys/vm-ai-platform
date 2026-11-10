"""Tests for the allowlisted, read-only Harness operational diagnostics."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from harness.mcp.tools import operational_tools


def test_operational_diagnostics_requires_environment_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPS_HARNESS_READONLY_SERVICES", raising=False)

    with pytest.raises(RuntimeError, match="SPS_HARNESS_READONLY_SERVICES"):
        operational_tools.operational_service_diagnostics("mongod")


def test_operational_diagnostics_rejects_unallowlisted_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPS_HARNESS_READONLY_SERVICES", "mongod")

    with pytest.raises(ValueError, match="not enabled"):
        operational_tools.operational_service_diagnostics("sshd")


def test_operational_diagnostics_runs_only_fixed_read_commands_and_redacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPS_HARNESS_READONLY_SERVICES", "mongod")

    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        commands.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout="mongodb://member:password-value@127.0.0.1:27017",
            stderr="token=token-value",
        )

    monkeypatch.setattr(operational_tools.subprocess, "run", fake_run)

    result = operational_tools.operational_service_diagnostics("mongod", journal_lines=999)

    assert result["service_name"] == "mongod"
    assert commands[0][:3] == ["systemctl", "show", "mongod"]
    assert commands[1][:3] == ["journalctl", "--unit", "mongod"]
    assert commands[1][-1] == "500"
    assert "password-value" not in result["service_state"]["stdout"]
    assert "token-value" not in result["service_state"]["stderr"]
