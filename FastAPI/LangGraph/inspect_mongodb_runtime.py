"""MongoDB 실행 주체(systemd 또는 Docker)를 변경 없이 확인합니다."""

from __future__ import annotations

import json
import subprocess


def _run(command: list[str]) -> dict:
    """명령의 상태만 수집하고 환경변수나 인증정보는 출력하지 않습니다."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip()[:500],
            "stderr": result.stderr.strip()[:500],
        }
    except Exception as exc:
        return {"returncode": None, "error_type": type(exc).__name__}


def main() -> None:
    """후보 실행 환경을 읽기 전용 명령으로 대조합니다."""
    checks = {
        "systemd_mongod": _run(["systemctl", "is-active", "mongod"]),
        "systemd_mongodb": _run(["systemctl", "is-active", "mongodb"]),
        # 시작 전 실패 원인을 확인해 저장소 잠금·권한·손상 상태에서 무리하게 재기동하지 않습니다.
        "mongod_status": _run(["systemctl", "status", "mongod", "--no-pager", "--lines", "20"]),
        "mongod_journal": _run([
            "journalctl", "-u", "mongod", "-n", "30", "--no-pager", "-o", "cat",
        ]),
        # 로그 기록 실패가 용량·inode·소유권 중 어디서 발생했는지 읽기 전용으로 구분합니다.
        "log_disk": _run(["df", "-h", "/var/log/mongodb"]),
        "log_inodes": _run(["df", "-i", "/var/log/mongodb"]),
        "log_permissions": _run([
            "stat", "-c", "%U|%G|%a|%s|%n",
            "/var/log/mongodb", "/var/log/mongodb/mongod.log",
        ]),
        "docker_container": _run([
            "docker", "ps", "-a", "--filter", "name=vm_7.12.0_mongo",
            "--format", "{{.Names}}|{{.Status}}",
        ]),
        "compose_mongo": _run(["docker", "compose", "ps", "mongo", "--format", "json"]),
    }
    print(json.dumps(checks, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
