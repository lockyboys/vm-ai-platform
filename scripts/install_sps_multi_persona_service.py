#!/usr/bin/env python3
"""Install and start the dedicated Multi-Persona systemd unit."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path("/data/vm_project")
UNIT_SOURCE = ROOT / "systemd" / "sps-multi-persona.service"
UNIT_NAME = "sps-multi-persona.service"
UNIT_TARGET = Path("/etc/systemd/system") / UNIT_NAME


def run(*args: str) -> str:
    completed = subprocess.run(
        list(args),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def main() -> None:
    if not UNIT_SOURCE.is_file():
        raise FileNotFoundError(UNIT_SOURCE)

    run(
        "sudo",
        "install",
        "-o",
        "root",
        "-g",
        "root",
        "-m",
        "0644",
        str(UNIT_SOURCE),
        str(UNIT_TARGET),
    )
    run("sudo", "systemctl", "daemon-reload")
    run("sudo", "systemctl", "enable", UNIT_NAME)
    run("sudo", "systemctl", "start", UNIT_NAME)
    print(run("sudo", "systemctl", "is-enabled", UNIT_NAME))
    print(run("sudo", "systemctl", "is-active", UNIT_NAME))


if __name__ == "__main__":
    main()
