"""크레딧 부족(402)·키 오류(401) 즉시 정지 패치 (2026-11-14, LuckyBoys 요청).

source_patch가 config.py에 적용되지 않아(줄 끝 형식 차이로 추정, 미확인) 정확한 문자열 치환으로 고친다.
- 각 치환 대상 문자열은 파일에 정확히 1번 있어야 한다(아니면 아무 파일도 바꾸지 않고 멈춤).
- 실제 반영 때는 원본을 <파일>.bak_20261114_fatal 로 먼저 보존한다(원본 보존 지침).
- 사용: sys.argv[1] == "--apply" 이면 반영, 아니면 dry-run(검사만).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPLY = len(sys.argv) > 1 and sys.argv[1] == "--apply"

CONFIG_OLD = "MULTI_PERSONA_REVIEW_WEB_SEARCH = False\n"
CONFIG_NEW = CONFIG_OLD + '''# 2026-11-14 (LuckyBoys 요청): 다시 불러도 소용없는 LLM 공급자 오류(크레딧 소진·키 오류)는 바로 멈추고 보고한다.
# 오류 문장에 키(소문자로 비교)가 들어 있으면 값(보고용 이유)으로 판정한다. 429 같은 일시 오류는 넣지 않는다.
# 숫자 '402'만으로는 판정하지 않는다(일반 문장의 숫자와 헷갈리지 않게 공급자 오류 문구와 함께 적는다).
MULTI_PERSONA_FATAL_PROVIDER_ERRORS = {
    "credits are depleted": "LLM 크레딧 부족(402)",
    "402 resource_exhausted": "LLM 크레딧 부족(402)",
    "402 payment required": "LLM 크레딧 부족(402)",
    "invalid_api_key": "LLM API 키 오류(401)",
    "error code: 401": "LLM API 키 오류(401)",
}
# 리뷰 CLI가 치명적 오류로 멈출 때 출력하는 표시 줄의 머리말과 종료 코드.
# 앱(harness/mcp/tools/multi_persona_tools.py)은 이 머리말로 멈춘 이유를 찾아 결과에 보고한다.
MULTI_PERSONA_FATAL_PROVIDER_MARKER = "[치명적 공급자 오류]"
MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE = 3
'''

COMMON_OLD = '    raise RuntimeError("no ollama candidate responded: " + json.dumps(tried, ensure_ascii=False))\n'
COMMON_NEW = COMMON_OLD + '''

# =============================================================================
# 2026-11-14 (LuckyBoys 요청): LLM 크레딧 부족(402)·키 오류(401)는 바로 멈추고 보고
# 배경: Gemini 402 "prepayment credits are depleted"를 '잠시 후 다시 시도'로 처리해
#       리뷰 한 번에 402 호출이 8번 반복됐고, 자가 수정 앱은 같은 라운드를 또 시도했다.
# =============================================================================
def fatal_provider_error_reason(error_text: str) -> str | None:
    """LLM 오류 문장이 '다시 불러도 소용없는 오류'인지 판정해 보고용 이유를 돌려준다.

    - 판정표: config.MULTI_PERSONA_FATAL_PROVIDER_ERRORS (키를 소문자로 비교, 설정 순서대로 첫 일치)
    - 치명적이 아니면(429 일시 오류, 일반 문장) None
    - 문자열이 아닌 입력은 ValueError (bytes·None을 조용히 '정상'으로 넘기지 않음)
    """
    if not isinstance(error_text, str):
        raise ValueError(f"error_text must be str, got {type(error_text).__name__}")
    import config as _config  # 테스트에서 설정을 바꿔도 반영되게 호출 시점에 읽는다
    lowered = error_text.lower()
    for pattern, reason in _config.MULTI_PERSONA_FATAL_PROVIDER_ERRORS.items():
        if pattern.lower() in lowered:
            return reason
    return None


def stop_on_fatal_provider_error(error_text: str, node_name: str) -> None:
    """치명적 공급자 오류이면 표시 줄을 출력하고 프로세스를 끝낸다(SystemExit). 아니면 None.

    표시 줄: "<MULTI_PERSONA_FATAL_PROVIDER_MARKER> <이유> — 리뷰를 멈춥니다. 노드=<node_name> 원문=<앞 300자>"
    종료 코드: config.MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE
    SystemExit는 Exception이 아니어서 LangGraph 노드의 일반 except에 잡히지 않고 그래프 전체를 멈춘다.
    """
    reason = fatal_provider_error_reason(error_text)
    if reason is None:
        return None
    import config as _config
    print(f"{_config.MULTI_PERSONA_FATAL_PROVIDER_MARKER} {reason} — 리뷰를 멈춥니다. "
          f"노드={node_name} 원문={' '.join(error_text.split())[:300]}", flush=True)
    raise SystemExit(int(_config.MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE))
'''

CLI_OLD = '''        print(f"🔥 [{node_name} 치명적 에러 발생]: {error_msg}")
'''
CLI_NEW = CLI_OLD + '''        # 2026-11-14 (LuckyBoys 요청): 크레딧 부족(402)·키 오류(401)는 다시 불러도 소용없으므로
        # 경고 답을 만들어 다음 노드로 넘기지 않고, 표시 줄을 출력한 뒤 프로세스를 바로 끝낸다.
        # (예전: '할당량 초과, 잠시 후 다시 시도' 답을 돌려주고 노드마다 다시 호출 → job 하나에 402 8번)
        from common.common_function import stop_on_fatal_provider_error
        stop_on_fatal_provider_error(error_msg, node_name)
'''

TOOLS_HELPER_OLD = "def _round_temperature(number) -> float:\n"
TOOLS_HELPER_NEW = '''def _provider_fatal(text: str) -> str | None:
    """리뷰 CLI 출력에서 치명적 공급자 오류 표시 줄(크레딧 부족 402·키 오류 401)을 찾는다(2026-11-14).

    표시 줄 머리말은 config.MULTI_PERSONA_FATAL_PROVIDER_MARKER. 있으면 그 줄(최대 500자), 없으면 None.
    이 줄이 있으면 다시 시도해도 같은 오류이므로 재시도·다음 라운드를 하지 않고 결과에 보고한다.
    """
    marker = project_config.MULTI_PERSONA_FATAL_PROVIDER_MARKER
    for line in text.splitlines():
        if line.startswith(marker):
            return line.strip()[:500]
    return None


''' + TOOLS_HELPER_OLD

TOOLS_ROUND_OLD = '''        if completed.returncode != 0 or not verified:
            rounds.append({**entry, "returncode": completed.returncode, "reasons": reasons})
            if completed.returncode == 0 and attempt < format_retries:
'''
TOOLS_ROUND_NEW = '''        # 2026-11-14: 크레딧 부족(402)·키 오류(401)로 멈췄으면 이유를 남기고 같은 라운드 재시도도 하지 않는다.
        fatal = _provider_fatal(text)
        if completed.returncode != 0 or not verified:
            rounds.append({**entry, "returncode": completed.returncode, "reasons": reasons,
                           **({"provider_fatal_error": fatal} if fatal else {})})
            if completed.returncode == 0 and not fatal and attempt < format_retries:
'''

TOOLS_JOB_OLD = '''    else:
        auto_result = {"auto_apply": True, "applied": False, "rolled_back": False,
                       "reason": "review not verified"}
'''
TOOLS_JOB_NEW = '''    else:
        # 2026-11-14: 크레딧 부족(402)·키 오류(401)로 멈췄으면 그 이유를 그대로 보고한다.
        auto_result = {"auto_apply": True, "applied": False, "rolled_back": False,
                       "reason": provider_fatal or "review not verified"}
'''
TOOLS_DETECT_OLD = '''    stderr = _mask_secrets(errors.decode("utf-8", errors="replace"))
    source = _project_path(request["source_path"], "source_path")
'''
TOOLS_DETECT_NEW = '''    stderr = _mask_secrets(errors.decode("utf-8", errors="replace"))
    # 2026-11-14: 리뷰 CLI가 치명적 공급자 오류(크레딧 부족 402·키 오류 401)로 멈췄는지 확인한다.
    provider_fatal = _provider_fatal(text + "\\n" + stderr)
    source = _project_path(request["source_path"], "source_path")
'''
TOOLS_RESULT_OLD = '''    limit = request["output_limit"]
    result.update(state="timed_out" if timed_out else ("completed" if success else "failed"),
'''
TOOLS_RESULT_NEW = '''    # 2026-11-14: 재시도 라운드에서 치명적 공급자 오류로 멈췄으면 그 이유도 결과 맨 위 항목으로 올린다.
    if provider_fatal is None and rounds and isinstance(rounds[-1], dict):
        provider_fatal = rounds[-1].get("provider_fatal_error")
    limit = request["output_limit"]
    result.update(state="timed_out" if timed_out else ("completed" if success else "failed"),
                  provider_fatal_error=provider_fatal,
'''

PLAN = {
    "config.py": [(CONFIG_OLD, CONFIG_NEW)],
    "common/common_function.py": [(COMMON_OLD, COMMON_NEW)],
    "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py": [(CLI_OLD, CLI_NEW)],
    "harness/mcp/tools/multi_persona_tools.py": [
        (TOOLS_HELPER_OLD, TOOLS_HELPER_NEW), (TOOLS_ROUND_OLD, TOOLS_ROUND_NEW),
        (TOOLS_JOB_OLD, TOOLS_JOB_NEW), (TOOLS_DETECT_OLD, TOOLS_DETECT_NEW),
        (TOOLS_RESULT_OLD, TOOLS_RESULT_NEW)],
}


def main() -> int:
    """모든 치환을 먼저 검사하고(1번씩 있는지), 모두 통과할 때만 반영한다."""
    updated, problems = {}, []
    for rel, pairs in PLAN.items():
        path = ROOT / rel
        raw = path.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for old, new in pairs:
            count = text.count(old)
            print(f"[검사] {rel}: 대상 {count}회 (CRLF={crlf}) :: {old.strip().splitlines()[0][:60]}")
            if count != 1:
                problems.append(f"{rel}: {count}회")
                continue
            text = text.replace(old, new)
        if crlf:
            text = text.replace("\n", "\r\n")
        updated[rel] = (raw, text.encode("utf-8"))
    if problems:
        print("[중단] 대상이 정확히 1번이 아님:", problems)
        return 1
    if not APPLY:
        print("[dry-run] 모든 대상 확인됨. 파일은 바꾸지 않았습니다.")
        return 0
    for rel, (raw, new_bytes) in updated.items():
        path = ROOT / rel
        backup = path.with_name(path.name + ".bak_20261114_fatal")
        if not backup.exists():
            backup.write_bytes(raw)
        path.write_bytes(new_bytes)
        compile(new_bytes.decode("utf-8"), str(path), "exec")  # 문법 확인
        print(f"[반영] {rel} (백업 {backup.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
