# =============================================================================
# File Name   : harness/mcp/tools/operational_tools.py
# Purpose     : 서버 서비스가 정상인지 읽기만 하는 점검 도구
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260902 | Codex | Harness 표준 파일 헤더와 서비스 진단 제한 기준을 보강했음
# =============================================================================
# 이 파일은 무엇을 하나요?
# - 허용 목록에 있는 서비스의 실행 상태와 최근 기록을 보여 줍니다.
# - 문제가 생겼을 때 서비스가 왜 멈췄는지 확인하는 데 씁니다.
# 주의: 서비스를 시작·중지·재시작하지 않고, 비밀값은 가려서 보여 줍니다.
"""Read-only operational diagnostics for explicitly allowed systemd services."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any

SERVICE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9@_.-]+$")
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)(password|passwd|secret|token|authorization|mongodb://[^\s]+:)(\s*[=:]\s*|[^\s]*:)[^\s,;]+"
)


def _allowed_service_names() -> set[str]:
    configured_services = os.getenv("SPS_HARNESS_READONLY_SERVICES", "")
    services = {service.strip() for service in configured_services.split(",") if service.strip()}
    if not services:
        raise RuntimeError("SPS_HARNESS_READONLY_SERVICES is required for operational diagnostics.")
    if any(SERVICE_NAME_PATTERN.fullmatch(service) is None for service in services):
        raise RuntimeError("SPS_HARNESS_READONLY_SERVICES contains an invalid service name.")
    return services


def _redact_sensitive_values(value: str) -> str:
    """Remove common credential forms before journal output leaves the host."""
    return SENSITIVE_VALUE_PATTERN.sub(lambda match: f"{match.group(1)}=***REDACTED***", value)


def _run_read_only(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    return {
        "return_code": result.returncode,
        "stdout": _redact_sensitive_values(result.stdout),
        "stderr": _redact_sensitive_values(result.stderr),
    }


def operational_service_diagnostics(service_name: str, journal_lines: int = 100) -> dict[str, Any]:
    """Read status and recent journal entries for one environment-allowlisted service."""
    normalized_service_name = service_name.strip()
    if normalized_service_name not in _allowed_service_names():
        raise ValueError("The requested service is not enabled for Harness diagnostics.")

    normalized_journal_lines = max(1, min(journal_lines, 500))
    return {
        "service_name": normalized_service_name,
        "service_state": _run_read_only(
            [
                "systemctl",
                "show",
                normalized_service_name,
                "--no-page",
                "--property=Id,LoadState,ActiveState,SubState,Result,MainPID,ExecMainStatus",
            ]
        ),
        "journal": _run_read_only(
            [
                "journalctl",
                "--unit",
                normalized_service_name,
                "--no-pager",
                "--output=short-iso",
                "--lines",
                str(normalized_journal_lines),
            ]
        ),
    }
