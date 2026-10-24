"""중단된 mongod를 데이터 삭제 없이 시작하고 상태를 검증합니다."""

from __future__ import annotations

import json
import socket
import subprocess
import time


def _run(command: list[str]) -> dict:
    """운영 명령의 종료 코드와 제한된 출력만 반환합니다."""
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip()[:500],
        "stderr": result.stderr.strip()[:500],
    }


def main() -> None:
    """systemd 시작 후 27017 포트가 실제로 열렸는지 확인합니다."""
    start = _run(["sudo", "-n", "systemctl", "start", "mongod"])
    time.sleep(3)
    active = _run(["systemctl", "is-active", "mongod"])
    try:
        with socket.create_connection(("127.0.0.1", 27017), timeout=3):
            port_open = True
    except OSError:
        port_open = False
    print(json.dumps({
        "start": start,
        "active": active,
        "port_27017_open": port_open,
        "data_deleted": False,
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
