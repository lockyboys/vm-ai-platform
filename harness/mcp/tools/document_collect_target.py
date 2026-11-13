"""document_collect 대상 어댑터 — 범용 자기 수리 엔진이 실행하는 '수집 1회' 진입점 (2026-11-11 LuckyBoys).

역할(이것만 한다)
    수집기(public_document_catalog_collector.py)를 새 프로세스로 끝까지 실행하고, 결과 status.json 을
    stdout 마지막 줄에 JSON 한 줄로 출력한다. 건수 판정·수리·재실행·백그라운드 job 은 엔진
    (harness/mcp/agents/self_repair_engine.py) 이 맡는다 → 엔진의 json_min 판정이 status.success 를 목표와 비교.

실행 예 (엔진이 config.SELF_REPAIR_TARGETS['document_collect'] 의 args_template 로 호출)
    python -m harness.mcp.tools.document_collect_target --collect meritz 메리츠화재 1000

종료 코드
    0 : status.json 을 읽어 출력함(건수가 부족해도 0 — 부족 판정은 엔진 몫)
    1 : 입력 오류 또는 수집기가 status.json 을 남기지 못함(stderr 에 사유 → 엔진은 '판독 불가'로 수리 대상 처리)

설정: 루트 config.py 의 SELF_REPAIR_COLLECT (일반 지침 4). 사이트 이름·URL 은 코드에 없다.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import config as project_config  # 루트 공통 설정(일반 지침 4)
from harness.mcp.tools.multi_persona_tools import PROJECT_ROOT

_SETTINGS = project_config.SELF_REPAIR_COLLECT
NAME_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")      # 수집기 프로파일 이름 규칙과 같다
MAX_COMPANY_CHARS = 100                                # 회사명 길이 상한(한 줄)
DOCUMENT_KEYWORD = "약관"                              # 이번 대상의 문서 종류(LuckyBoys: 약관만)
STDERR_TAIL = 3000                                     # 수집기 오류 출력 중 엔진 증빙으로 넘길 끝부분


def validate_request(name: Any, company_name: Any, expected_min_count: Any) -> dict:
    """명령행 입력 검사. 목표 건수는 명령행이라 숫자 문자열도 받되 1 이상 정수여야 한다."""
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise ValueError("name must match [a-z0-9_]{1,64}")
    if (not isinstance(company_name, str) or not 1 <= len(company_name.strip()) <= MAX_COMPANY_CHARS
            or any(ch in company_name for ch in "\r\n\t")):
        raise ValueError(f"company_name must be 1..{MAX_COMPANY_CHARS} chars on one line")
    if isinstance(expected_min_count, bool):
        raise ValueError("expected_min_count must be an integer >= 1")
    if isinstance(expected_min_count, str) and expected_min_count.isdigit():
        expected_min_count = int(expected_min_count)
    if not isinstance(expected_min_count, int) or expected_min_count < 1:
        raise ValueError("expected_min_count must be an integer >= 1")
    return {"name": name, "company_name": company_name.strip(), "expected_min_count": expected_min_count,
            "document_keyword": DOCUMENT_KEYWORD}


def _load_collector():
    """수집기 모듈을 경로로 연결한다(패키지 import 경로가 없어 importlib 사용)."""
    script = Path(str(_SETTINGS["collector_script"]))
    spec = importlib.util.spec_from_file_location("document_collect_target_collector", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_collector_subprocess(request: dict) -> tuple[dict, str, str]:
    """수집기를 새 프로세스로 끝까지 실행하고 (status, status 경로, 수집기 stderr 끝부분)을 돌려준다.

    - 프로파일이 없으면(처음 보는 회사): parse_onboard 로 onboard_request.json 을 만들고 --onboard
      (공시실 웹 검색 → 탐색·수리 → 수집). parse_onboard 는 프로파일이 있으면 거부하므로 분기한다.
    - 프로파일이 있으면(재수집·수리 후 재검증): --worker (카탈로그·다운로드 이어받기).
    - 새 프로세스로 돌리는 이유: 수리로 바뀐 수집기 코드를 매번 새로 읽기 위해서다.
    """
    collector = _load_collector()
    name = request["name"]
    limit = min(int(_SETTINGS["collect_time_limit_seconds"]), int(collector.MAX_TIME_LIMIT_SECONDS))
    out = collector.output_dir({"name": name})
    if (collector.PROFILE_DIR / f"{name}.json").exists():
        arguments = ["--worker", name, str(limit)]
    else:
        onboard = collector.parse_onboard({"profile": name, "company_name": request["company_name"],
                                           "document_keyword": request["document_keyword"],
                                           "time_limit_seconds": limit})
        collector.atomic_json(out / "onboard_request.json", onboard)
        arguments = ["--onboard", name, str(limit)]
    done = subprocess.run([sys.executable, str(_SETTINGS["collector_script"]), *arguments],
                          cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                          timeout=limit + int(_SETTINGS["collector_grace_seconds"]))
    status_path = out / "status.json"
    tail = (done.stderr or "")[-STDERR_TAIL:]
    if not status_path.is_file():
        raise RuntimeError(f"collector wrote no status.json: {status_path}\n{tail}")
    return json.loads(status_path.read_text(encoding="utf-8")), str(status_path), tail


def normalize_success(status: dict) -> dict:
    """엔진 json_min 판정용으로 success 를 항상 정수로 맞춘다 (2026-11-12 메리츠 판정 불일치 수정).

    수집기는 다운로드 단계에서만 success(받은 건수)를 쓴다. 탐색(DISCOVER) 단계에서 실패하면 키가 없어서
    엔진이 KeyError → 'unreadable' 로만 보고했고 몇 건인지 알 수 없었다(job da702ac6…).
    정수가 아니거나 없으면 '받은 건수 0' 으로 보고 success_missing=True 로 표시한다(숨기지 않음).
    bool 은 int 하위형이라 따로 거부한다. 원래 status 의 다른 값은 그대로 둔다.
    """
    value = status.get("success")
    if isinstance(value, bool) or not isinstance(value, int):
        return {**status, "success": 0, "success_missing": True}
    return {**status, "success_missing": False}


def main(argv: list[str], run_collector: Callable[[dict], tuple[dict, str, str]] = None) -> int:
    """'--collect name company expected' → 수집 → status 를 stdout 마지막 줄 JSON 으로 출력."""
    if len(argv) != 4 or argv[0] != "--collect":
        print("usage: --collect <name> <company_name> <expected_min_count>", file=sys.stderr)
        return 1
    try:
        request = validate_request(argv[1], argv[2], argv[3])
        status, status_path, collector_stderr = (run_collector or run_collector_subprocess)(request)
    except Exception as error:  # noqa: BLE001 - 실패를 숨기지 않고 stderr 로 남긴다(엔진 증빙)
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1
    if collector_stderr:
        print(collector_stderr, file=sys.stderr)             # 수리 작업문 증빙용
    status = normalize_success(status)                       # success 없음 → 0 + 표시(판정: shortfall)
    print(json.dumps({**status, "status_path": status_path}, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
