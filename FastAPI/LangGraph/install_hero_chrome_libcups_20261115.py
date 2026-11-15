"""Ulixee Hero(Chrome) 실행에 필요한 libcups 설치 (2026-11-15, LuckyBoys 요청).

배경: 메리츠화재 상품공시 probe에서 Hero가 "missing: libcups.so.2"로 Chrome을 띄우지 못했다.
순서
1. apt-cache policy(sudo 없음)로 이 서버에 있는 패키지 이름을 고른다
   (Ubuntu 24.04 이상은 libcups2t64, 그 이전은 libcups2). 둘 다 없으면 설치하지 않고 멈춘다.
2. common.common_function.run_allowed_sudo 로 허용 목록(config.SUDO_ALLOWED_COMMANDS) 안에서만 설치한다.
3. ldconfig -p(sudo 없음)로 libcups.so.2가 보이는지 확인해 결과를 출력한다.
이 스크립트는 mcp_codex_apps_run_python_source가 sudo 사용을 찾아내 LuckyBoys 승인 뒤에만 실행된다.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from common.sudo_runner import run_allowed_sudo  # noqa: E402 - 2026-11-15: sudo 전용 모듈로 옮김

CANDIDATES = ("libcups2t64", "libcups2")  # 새 이름부터 확인


def has_candidate(package: str) -> bool:
    """apt-cache policy 결과에 설치 후보(Candidate)가 있으면 True (sudo 불필요)."""
    out = subprocess.run(["apt-cache", "policy", package], capture_output=True, text=True, timeout=60).stdout
    return any(line.strip().startswith("Candidate:") and "(none)" not in line for line in out.splitlines())


def libcups_visible() -> bool:
    """ldconfig -p 에 libcups.so.2 가 있으면 True (설치 확인, sudo 불필요)."""
    out = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True, timeout=30).stdout
    return "libcups.so.2" in out


def main() -> int:
    before = libcups_visible()
    package = next((name for name in CANDIDATES if has_candidate(name)), None)
    report = {"libcups_before": before, "package": package}
    if before:
        report["result"] = "이미 설치되어 있어 설치하지 않음"
    elif package is None:
        report["result"] = "설치 후보 패키지 없음(apt 저장소 확인 필요) — 설치하지 않음"
    else:
        report["install"] = run_allowed_sudo(["apt-get", "install", "-y", package], dry_run=False)
        report["libcups_after"] = libcups_visible()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if (before or report.get("libcups_after")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
