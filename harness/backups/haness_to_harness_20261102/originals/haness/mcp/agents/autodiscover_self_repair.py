"""자동 탐색 자기 수리 루프 (2026-10-25 LuckyBoys: "스스로 고치는 프로그램", 권한 = "자동 적용 + add만").

위치: SPS Harness 소스이므로 haness/ 아래에 둔다(일반 지침 10). 설정은 루트 config.py,
      공통 함수는 common/common_function.py를 쓴다(일반 지침 4).
      DB 저장 요청이 없어 DB 연결·변경은 하지 않는다(common.database 미사용 — 수집기와 같은 기준).
      수리 증빙을 DB(harness_source_audit 등)에 남기려면 테이블·필드 COMMENT 확인 후 별도 승인으로 추가한다.

왜 필요한가
    profile_autodiscover.auto는 처음 보는 실패를 NEEDS_NEW_RULE로 멈추고 증빙만 남긴다.
    그 다음 "규칙을 고치는 일"을 사람이 하지 않도록, 이 모듈이 증빙을 PARTNER 에이전트
    (haness/mcp/agents/source_partner_agent.py → change_set_graph)에 넘겨 코드를 고치게 한다.

수리 범위는 "적용 전에" 막는다(사후 원복이 아님 — 원본 보존, 일반 지침 7)
    PARTNER의 execute_change_set에 allowed_source_paths를 넘겨, 다음은 적용 전에 거부된다.
      - 허용 소스(config.AUTODISCOVER_SELF_REPAIR['allowed_paths']) 밖 파일의 patch
      - 기존 테스트 수정(테스트를 고쳐 억지로 통과시키는 것 방지). haness/tests/ 아래 '새 파일 추가'만 허용
      - stage 대상이 위 두 가지 밖인 경우

흐름 (한 번 실행에서 최대 max_repair_rounds회)
    1) auto를 새 프로세스로 실행(고친 코드를 매번 새로 읽기 위해)
    2) NEEDS_NEW_RULE이면: 허용 소스 백업 → 수리 작업문 → PARTNER 실행
       (change_set_graph: patch dry-run → 적용 → pytest → git add, 실패 시 자체 롤백)
    3) 이 모듈이 다시 확인: 실제 staged 변경이 있는지 / 회귀 테스트 통과인지
       - 회귀 실패면 허용 소스를 백업으로 되돌리고 REPAIR_FAILED (에이전트가 새로 만든 테스트 파일은
         지우지 않고 new_test_files로 보고한다 — 삭제는 사람이 판단)
    4) 통과하면 auto를 다시 실행해 실제 사이트로 재검증
    커밋은 하지 않는다(commit_confirmed=False 고정).

입력 (stdin JSON): {"name": "<프로파일 [a-z0-9_]>", "apply": true, "start_urls": [...선택], "document_keyword": "약관"}
출력: stdout JSON 보고서 + config.AUTODISCOVER_SELF_REPAIR['report_dir']/<name>/repair_<시각>.json 증빙
"""
from __future__ import annotations

import asyncio
import json
import re
import traceback
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402 - 루트 공통 설정(일반 지침 4)
from common.common_function import now_kst_iso, write_json_atomic  # noqa: E402 - 공통 함수(일반 지침 4)

_SETTINGS = config.AUTODISCOVER_SELF_REPAIR
NAME_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")
MAX_TASK_CHARS = 12000          # run_source_partner_agent의 작업문 상한과 같다
MAX_EVIDENCE_CHARS = 4000       # 작업문에 넣는 실패 증빙 파일 내용 상한
FIXED_RESULTS = ("DISCOVERED", "EXISTING_PROFILE_VALID")   # 이 접두어면 "고쳐짐/정상"

# 오류 기록 최대 길이 (describe_error 출력이 이 값을 넘지 않는다)
MAX_ERROR_DETAIL_CHARS = 2000


def describe_error(error: BaseException) -> str:
    """오류의 종류·메시지·발생 위치를 문자열로 요약한다.

    ExceptionGroup(asyncio TaskGroup 등)인 경우 재귀적으로 내부 원인을 풀어
    실제 에러 종류·메시지·파일:줄 을 기록한다.
    일반 오류는 "ClassName: message" 형태.
    잘못된 입력(None, str, int 등)은 TypeError 를 발생시킨다.
    """
    if not isinstance(error, BaseException):
        raise TypeError(f"expected BaseException, got {type(error).__name__}")

    parts: list[str] = []

    def _collect(exc: BaseException, depth: int = 0) -> None:
        prefix = type(exc).__name__
        if isinstance(exc, BaseExceptionGroup):
            parts.append(f"{prefix}: {exc.args[0] if exc.args else ''}")
            for sub in exc.exceptions:
                _collect(sub, depth + 1)
        else:
            location = ""
            tb = exc.__traceback__
            if tb is not None:
                frames = traceback.extract_tb(tb)
                if frames:
                    last = frames[-1]
                    location = f" @ {last.filename}:{last.lineno}"
            parts.append(f"{prefix}: {exc}{location}")

    _collect(error)
    text = " -> ".join(parts) if len(parts) > 1 else (parts[0] if parts else str(error))
    return text[:MAX_ERROR_DETAIL_CHARS]


def _stamp() -> str:
    """증빙·백업 파일명에 쓰는 KST 시각(YYYYMMDD_HHMMSS)."""
    return now_kst_iso()[:19].replace("-", "").replace(":", "").replace("T", "_")


def _work_dir(name: str) -> Path:
    """수리 증빙 폴더. Harness 산출물이므로 config의 haness/reports/autodiscover_repair/<이름> 아래(일반 지침 10)."""
    path = Path(str(_SETTINGS["report_dir"])) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# 순수 함수 (테스트 대상)
# ---------------------------------------------------------------------------
def build_repair_task(name: str, report: dict) -> str:
    """NEEDS_NEW_RULE 보고서로 PARTNER에게 줄 한국어 작업문을 만든다(12000자 이하).

    승인 값(source_write/commit)과 수리 범위는 작업문이 아니라 호출 경계에서 고정되므로
    여기서는 안내만 한다(모델이 무시해도 execute_change_set이 적용 전에 거부한다).
    """
    failure = report.get("failure") or {}
    evidence_text = ""
    evidence_path = failure.get("evidence") or ""
    if evidence_path and Path(evidence_path).is_file():
        evidence_text = Path(evidence_path).read_text(encoding="utf-8", errors="replace")[:MAX_EVIDENCE_CHARS]
    allowed = "\n".join(f"  - {p}" for p in _SETTINGS["allowed_paths"])
    tests = json.dumps(_SETTINGS["regression_tests"], ensure_ascii=False)
    task = f"""[자동 탐색 자기 수리] 프로파일 '{name}' 자동 탐색이 처음 보는 유형의 실패로 멈췄다(NEEDS_NEW_RULE).
오류 유형: {failure.get('category', '미확인')}
오류: {str(failure.get('error', ''))[:800]}
증빙 파일: {evidence_path or '없음'}
증빙 내용(앞부분):
{evidence_text}

해야 할 일:
1. read_repair_source로 아래 파일을 읽고(sha256 확인) 이 오류가 나는 원인을 코드에서 찾는다.
2. 이 오류를 재현하는 unittest(regression_test, 잘못된 입력 포함)를 만든다. SOURCE_PATH 변수의 후보 파일을
   대상으로 하고(import 부작용이 있으면 AST로 대상 함수만 분리), 네트워크·브라우저 없이. 원본에서는 실패해야 한다.
3. 원인을 고치는 최소 변경을 old_code(파일에 정확히 한 번 나오는 원문) → new_code로 만든다.
   고칠 수 있는 소스는 이것뿐이다(그 밖은 거부됨):
{allowed}
4. repair_source 한 번으로 실행한다(원본 실패·후보 통과 확인 → 백업 → 적용 → git add까지만, 커밋 안 함).
   PRE_COMMIT_REQUIRED가 오면 고치지 말고 그대로 보고한다. 적용 뒤 프로그램이 다음 회귀 테스트를 실행한다: {tests}
규칙: 특정 사이트 이름·URL·필드명을 코드에 하드코딩하지 않는다(사이트 비종속 엔진). 관련 없는 코드·주석은 바꾸지 않는다.
주석은 한국어로 자세히 단다. 도구 결과에 없는 성공을 주장하지 말고, 못 고치면 못 고쳤다고 보고한다."""
    return task[:MAX_TASK_CHARS]


def staged_change_sets(agent_result: dict) -> list[dict]:
    """PARTNER 도구 증빙에서 '실제 적용되고 성공한' 변경 세트만 고른다(dry-run·실패·비JSON 제외).

    2026-10-25 LuckyBoys: 수리 엔진을 haness/source_repair.py 하나로 통일 → 그 보고서도 인정한다.
      - source_repair 보고서: success·applied True, dry_run False, path 있음, git_stage.staged True(git add까지 됨)
        → changed_paths·regression_now가 그대로 쓰도록 change_set 모양으로 바꿔 돌려준다.
      - 예전 change_set 보고서(change_set_id·staged_groups)는 그대로 인정(기존 동작 유지).
    """
    found = []
    for item in agent_result.get("tool_evidence") or []:
        try:
            value = json.loads(item.get("content", ""))
        except (TypeError, ValueError):
            continue
        if not isinstance(value, dict):
            continue
        if (value.get("success") is True and value.get("applied") is True and value.get("dry_run") is False
                and isinstance(value.get("path"), str) and value["path"]
                and (value.get("git_stage") or {}).get("staged") is True):
            found.append({"change_set_id": f"source_repair:{str(value.get('after_sha256', ''))[:12]}",
                          "success": True, "dry_run": False, "engine": "source_repair",
                          "staged_groups": {"source": [value["path"]]}, "report": value})
        elif (value.get("change_set_id") and value.get("success") is True
                and value.get("dry_run") is False and value.get("staged_groups")):
            found.append(value)
    return found


def changed_paths(change_sets: list[dict]) -> list[str]:
    """변경 세트들이 stage한 모든 경로(정렬, 중복 제거)."""
    return sorted({p for cs in change_sets for paths in cs["staged_groups"].values() for p in paths})


def heal_succeeded(report: dict) -> bool:
    """재탐색/수리 결과를 '고쳐짐'으로 볼지 판단(NEEDS_NEW_RULE·REPAIR_*·FAILED는 실패)."""
    return str((report or {}).get("result", "")).startswith(FIXED_RESULTS)


# ---------------------------------------------------------------------------
# 실제 실행 함수 (테스트에서는 주입으로 교체)
# ---------------------------------------------------------------------------
def run_auto_subprocess(request: dict) -> dict:
    """profile_autodiscover auto를 새 파이썬 프로세스로 실행한다(수리된 코드를 새로 읽기 위해)."""
    payload = {k: v for k, v in request.items() if k in {"name", "apply", "start_urls", "document_keyword"}}
    payload["mode"] = "auto"
    done = subprocess.run([sys.executable, str(_SETTINGS["autodiscover_script"])],
                          input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True,
                          cwd=ROOT, timeout=int(_SETTINGS["auto_timeout_seconds"]))
    if done.returncode != 0:
        return {"result": "FAILED", "error": f"auto exited {done.returncode}: {done.stderr[-800:]}"}
    return json.loads(done.stdout)


def run_partner(task: str, round_no: int = 1) -> dict:
    """페르소나 체인(haness/mcp/agents/persona_repair_chain.py)으로 수리한다.

    2026-10-25 LuckyBoys: 1라운드는 고정 순서 체인, 2라운드부터 ORCHESTRATOR 자율 계획(마지막 PARTNER만 지정).
    회귀 테스트 실행은 체인 안에서 프로그램이 한다. 체인 예외는 실패(verdict=ERROR)로 보고한다.
    """
    from haness.mcp.agents.persona_repair_chain import run_chain

    try:
        return run_chain(task, staged_fn=staged_change_sets, round_no=round_no)
    except BaseException as error:  # noqa: BLE001 - 체인 실패는 수리 실패로 보고(숨기지 않음)
        return {"verdict": "ERROR", "error": describe_error(error),
                "tool_evidence": [], "steps": []}


def backup_sources(paths: list[str]) -> dict[str, str]:
    """허용 소스를 파일명_BACKUP_날짜_시분초.확장자로 복사한다(원본 보존, 일반 지침 7)."""
    stamp, backups = _stamp(), {}
    for relative in paths:
        source = ROOT / relative
        backup = source.with_name(f"{source.stem}_BACKUP_{stamp}{source.suffix}")
        if source.is_file() and not backup.exists():
            shutil.copy2(source, backup)
            backups[relative] = str(backup)
    return backups


def restore_sources(backups: dict[str, str]) -> None:
    """허용 소스를 백업으로 되돌리고 git add 해서 stage도 원래 내용으로 맞춘다."""
    for relative, backup in backups.items():
        shutil.copy2(backup, ROOT / relative)
        subprocess.run(["git", "add", "--", relative], cwd=ROOT, capture_output=True, text=True, timeout=60)


# ---------------------------------------------------------------------------
# 루프
# ---------------------------------------------------------------------------
def _previous_attempt_text(entry: dict) -> str:
    """앞 라운드 실패 요약(판정·계획·단계별 산출물 앞부분)을 다음 라운드 작업문에 붙인다."""
    lines = [f"\n[이전 시도 {entry.get('round')}라운드] 결과: {entry.get('result')} / 계획: {entry.get('plan')}"]
    for step in entry.get("steps") or []:
        lines.append(f"- {step.get('persona')}({step.get('mode')}): {str(step.get('output', ''))[:400]}")
    if entry.get("regression"):
        lines.append(f"- 회귀 테스트: {str(entry['regression'].get('tail', ''))[-600:]}")
    return "\n".join(lines)


def auto_with_repair(request: dict, auto_fn: Callable[[dict], dict] = None, partner_fn: Callable[..., dict] = None,
                     backup_fn: Callable[[list], dict] = None, restore_fn: Callable[[dict], None] = None) -> dict:
    """auto → (NEEDS_NEW_RULE이면) 수리 → 확인 → auto 재실행. 결과·증빙 경로를 돌려준다."""
    if not isinstance(request, dict) or not isinstance(request.get("name"), str) \
            or not NAME_PATTERN.fullmatch(request["name"]):
        raise ValueError("request.name must match [a-z0-9_]{1,64}")
    auto_fn = auto_fn or run_auto_subprocess
    partner_fn = partner_fn or run_partner
    backup_fn = backup_fn or backup_sources
    restore_fn = restore_fn or restore_sources
    name = request["name"]

    report = auto_fn(request)
    out: dict[str, Any] = {"mode": "auto_repair", "name": name, "started_kst": now_kst_iso(),
                           "first_result": report.get("result"), "repairs": []}
    final_failure = None
    rounds = 0
    while report.get("result") == "NEEDS_NEW_RULE" and _SETTINGS["enabled"] \
            and rounds < int(_SETTINGS["max_repair_rounds"]):
        rounds += 1
        entry: dict[str, Any] = {"round": rounds, "failure": report.get("failure")}
        out["repairs"].append(entry)
        backups = backup_fn(list(_SETTINGS["allowed_paths"]))
        entry["backups"] = backups
        # 앞 라운드가 실패했으면 그 증빙을 붙여 다음 라운드(ORCHESTRATOR 자율 계획)에 넘긴다.
        task = build_repair_task(name, report) + (_previous_attempt_text(out["repairs"][-2]) if rounds > 1 else "")
        agent = partner_fn(task[:12000], rounds)
        entry["verdict"] = agent.get("verdict", "미확인")
        entry["mode"] = agent.get("mode")
        entry["plan"] = agent.get("plan")
        entry["personas"] = [s.get("persona") for s in agent.get("steps") or []]
        entry["steps"] = agent.get("steps") or []
        entry["regression"] = agent.get("regression")
        entry["agent_output"] = str(agent.get("output") or agent.get("error") or "")[:2000]
        sets = staged_change_sets(agent)
        entry["change_sets"] = [cs["change_set_id"] for cs in sets]
        entry["paths"] = changed_paths(sets)
        if not sets:
            # 적용·stage된 변경이 없음 = 못 고침(범위 위반 거부·change_set 자체 롤백·시도 안 함 포함)
            entry["result"], final_failure = "NO_CHANGE", "REPAIR_FAILED"
            continue   # 남은 라운드가 있으면 다음 라운드(ORCHESTRATOR 자율)로, 없으면 루프 조건에서 끝난다
        # REVIEWER HOLD·회귀 실패·TESTER 비통과면 체인 verdict가 PASS가 아니다 → 허용 소스 원복.
        if entry["verdict"] != "PASS":
            restore_fn(backups)
            entry["new_test_files"] = [p for p in entry["paths"] if p not in backups]
            entry["result"], final_failure = entry["verdict"], "REPAIR_FAILED"
            continue   # 원복 후 다음 라운드로(남은 라운드가 없으면 종료)
        entry["result"], final_failure = "STAGED", None
        # 고친 코드로 실제 사이트 재검증(새 프로세스). 또 NEEDS_NEW_RULE이면 남은 횟수만큼 반복.
        report = auto_fn(request)
        entry["after_result"] = report.get("result")

    out["final"] = {k: v for k, v in report.items() if k != "attempts"}
    out["result"] = final_failure or report.get("result", "FAILED")
    out["finished_kst"] = now_kst_iso()
    evidence = _work_dir(name) / f"repair_{_stamp()}.json"
    write_json_atomic(evidence, out)
    out["evidence"] = str(evidence)
    return out


def main() -> None:
    request = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(auto_with_repair(request), ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
