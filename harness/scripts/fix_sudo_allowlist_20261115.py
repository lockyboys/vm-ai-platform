"""허용 목록 sudo 실행 기능 추가 패치 (2026-11-15, LuckyBoys 요청).

source_patch가 config.py 끝(줄바꿈 없음)에 적용되지 않아(원인 미확인) 정확한 문자열 치환으로 넣는다.
- 대상 문자열은 파일에 정확히 1번 있어야 한다(아니면 아무 파일도 바꾸지 않고 멈춤).
- 반영 전 원본을 <파일>.bak_20261115_sudo 로 보존한다(원본 보존 지침).
- sys.argv[1] == "--apply" 이면 반영, 아니면 dry-run(검사만).
LuckyBoys 결정: rm -rf·kill·python3 -c·cat(보호 파일)은 무엇이든 할 수 있게 되므로 허용 목록에서 뺀다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPLY = len(sys.argv) > 1 and sys.argv[1] == "--apply"

CONFIG_OLD = 'GIT_UNCOMMIT_BACKUP_REF_PREFIX = "refs/harness-backup/uncommit"'
CONFIG_NEW = CONFIG_OLD + '''
# 2026-11-15 (LuckyBoys 결정): 허용 목록 sudo 실행(common.common_function.run_allowed_sudo).
# 새 MCP 도구 없이 mcp_codex_apps_run_python_source의 위험 명령 승인(approval_commands)을 거친 뒤에만 실행된다.
# 키: 명령 앞부분(고정), 값: 그 뒤에 올 수 있는 인자(모두 이 목록 안, 하나 이상). 값이 빈 튜플이면 인자 없이만.
# 뺀 것(LuckyBoys 결정): rm -rf, kill, python3 -c, cat(보호 파일) — 무엇이든 할 수 있게 되는 명령.
SUDO_ALLOWED_SERVICES = (
    "sps-harness.service", "sps-gemini-agent.service", "sps-multi-persona.service",
    "fastapi-insurance-rag.service", "mongod",
)
SUDO_ALLOWED_COMMANDS = {
    # 서비스 재시작·시작·정지·자동 시작 켜기/끄기·상태 확인
    ("systemctl", "restart"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "start"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "stop"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "enable"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "enable", "--now"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "disable"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "is-enabled"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "is-active"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "status", "--no-pager"): SUDO_ALLOWED_SERVICES,
    # 서비스 설정 다시 읽기(인자 없음)
    ("systemctl", "daemon-reload"): (),
    # sudo 권한 확인(인자 없음)
    ("-l",): (),
    # Ulixee Hero(Chrome) 실행에 필요한 라이브러리(2026-11-15: libcups.so.2 누락). OS 버전에 따라 이름이 다름.
    ("apt-get", "install", "-y"): ("libcups2", "libcups2t64"),
}
# sudo 명령 하나의 최대 실행 시간(초)
SUDO_TIMEOUT_SECONDS = 600
'''

COMMON_OLD = '    raise SystemExit(int(_config.MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE))'
COMMON_NEW = COMMON_OLD + '''


# =============================================================================
# 2026-11-15 (LuckyBoys 요청 "sudo 실행하는 도구 만들자", 선택: 기존 도구에 추가 + 허용 목록만)
# - 새 MCP 도구는 만들지 않는다. 이 함수를 부르는 FastAPI/LangGraph 스크립트를
#   mcp_codex_apps_run_python_source로 실행하면, 그 도구가 sudo 사용을 찾아내
#   approval_commands로 보여 주고 LuckyBoys 승인 뒤에만 실행한다.
# - 실행할 수 있는 명령은 config.SUDO_ALLOWED_COMMANDS 에 있는 것만이다.
# =============================================================================
import subprocess  # noqa: E402 - run_allowed_sudo 전용(테스트에서 대역으로 바꿀 수 있게 모듈 수준에 둔다)

_SUDO_ARG_PATTERN = re.compile(r"^[A-Za-z0-9._@:+=-]+$")  # 셸 특수문자(; | & $ ` / 공백 등) 차단


def run_allowed_sudo(command: list[str], dry_run: bool = True) -> dict:
    """허용 목록에 있는 sudo 명령만 셸 없이 실행한다(sudo -n: 암호를 묻지 않고, 권한 없으면 바로 실패).

    - command: ["apt-get", "install", "-y", "libcups2t64"] 처럼 리스트(문자열 하나는 거부: 셸 해석 위험)
    - 허용 판정: config.SUDO_ALLOWED_COMMANDS 의 키(명령 앞부분)로 시작해야 한다(긴 키부터 비교).
      값이 있으면 나머지 인자가 1개 이상이고 모두 값 안에 있어야 하며, 값이 빈 튜플이면 나머지 인자가 없어야 한다.
    - dry_run=True(기본): 실행하지 않고 실제로 돌릴 명령만 돌려준다.
    - 실행 결과: returncode, stdout/stderr 끝 2000자, timed_out(시간 초과는 예외 대신 결과로 보고)
    - 잘못된 입력은 sudo를 부르기 전에 ValueError.
    """
    if not isinstance(command, list) or not command:
        raise ValueError("command must be a non-empty list of strings")
    if any(not isinstance(arg, str) or not _SUDO_ARG_PATTERN.match(arg) for arg in command):
        raise ValueError(f"command has an empty or unsafe argument: {command!r}")
    import config as _config  # 테스트에서 허용 목록을 바꿔도 반영되게 호출 시점에 읽는다
    allowed = None
    for prefix in sorted(_config.SUDO_ALLOWED_COMMANDS, key=len, reverse=True):
        if tuple(command[:len(prefix)]) == tuple(prefix):
            allowed = (tuple(prefix), tuple(_config.SUDO_ALLOWED_COMMANDS[prefix]))
            break
    if allowed is None:
        raise ValueError(f"command is not in config.SUDO_ALLOWED_COMMANDS: {command!r}")
    prefix, values = allowed
    targets = command[len(prefix):]
    if values:
        if not targets or any(arg not in values for arg in targets):
            raise ValueError(f"arguments {targets!r} are not allowed for {' '.join(prefix)} (allowed: {list(values)})")
    elif targets:
        raise ValueError(f"{' '.join(prefix)} takes no arguments: {targets!r}")
    full = ["sudo", "-n", *command]
    plan = {"dry_run": dry_run, "command": full, "allowed_prefix": list(prefix)}
    if dry_run:
        return plan
    timeout = int(_config.SUDO_TIMEOUT_SECONDS)
    try:
        done = subprocess.run(full, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {**plan, "timed_out": True, "returncode": None, "stdout_tail": "", "stderr_tail": ""}
    return {**plan, "timed_out": False, "returncode": done.returncode,
            "stdout_tail": done.stdout[-2000:], "stderr_tail": done.stderr[-2000:]}
'''

PLAN = {"config.py": (CONFIG_OLD, CONFIG_NEW), "common/common_function.py": (COMMON_OLD, COMMON_NEW)}


def main() -> int:
    """모든 치환을 먼저 검사하고(정확히 1번 있는지, 이미 반영됐는지), 모두 통과할 때만 반영한다."""
    updated, problems = {}, []
    for rel, (old, new) in PLAN.items():
        path = ROOT / rel
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        count = text.count(old)
        already = "SUDO_ALLOWED_COMMANDS" in text if rel == "config.py" else "def run_allowed_sudo" in text
        print(f"[검사] {rel}: 대상 {count}회, 이미 반영={already}")
        if count != 1 or already:
            problems.append(rel)
            continue
        updated[rel] = (raw, text.replace(old, new).encode("utf-8"))
    if problems:
        print("[중단] 대상이 1번이 아니거나 이미 반영됨:", problems)
        return 1
    for rel, (_raw, new_bytes) in updated.items():
        compile(new_bytes.decode("utf-8"), rel, "exec")  # 반영 전 문법 확인
    if not APPLY:
        print("[dry-run] 모든 대상 확인·문법 통과. 파일은 바꾸지 않았습니다.")
        return 0
    for rel, (raw, new_bytes) in updated.items():
        path = ROOT / rel
        backup = path.with_name(path.name + ".bak_20261115_sudo")
        if not backup.exists():
            backup.write_bytes(raw)
        path.write_bytes(new_bytes)
        print(f"[반영] {rel} (백업 {backup.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
