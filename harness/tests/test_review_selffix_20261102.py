"""review_python_source 자가 수정 결함 재현·회귀 테스트 (2026-11-02, LuckyBoys 승인).

재현 대상(실제 사고, job 0fded59b903c4089a8006bdd796b460e):
  LLM이 실제로 있는 `-m` 모듈 경로를 오타로 오판해 존재하지 않는 패키지 이름으로 바꾼 제안 소스가
  문법 검사만 통과해 proposed.py로 저장되고 model_verified=true로 표시되었다.
  (당시는 haness -> harness. 2026-11-02 폴더 이동 이후에는 harness가 실제 패키지이므로,
   테스트는 실제 패키지 harness와 존재하지 않는 오타 패키지 harnessx로 같은 상황을 재현한다.)
검증 항목:
  1) validate_review가 존재하지 않는 import/`-m` 모듈을 오류로 반환한다.
  2) model_verified는 계약(import 포함)+LLM verifier+제안 파일 생성을 모두 만족해야 true다.
  3) 제안 파일은 job 전용 폴더에 저장되어 동시 리뷰가 서로 덮어쓰지 않는다.
  4) 리뷰 시간(3590)+결과 저장 여유(10)가 유닛 상한(3600) 안에 들어간다.
  5) 워커가 결과 없이 끝나면 실패 결과를 result.json에 영구 기록한다.
모든 테스트는 LLM·systemd·실제 리뷰를 실행하지 않는다.
"""
import asyncio
import json

import pytest

import config
from FastAPI.LangGraph.multi_persona.review_contract import HEADINGS, build_review_query, validate_review
from harness.mcp.tools import multi_persona_tools as review


# ---------------------------------------------------------------------------
# 공통 도우미
# ---------------------------------------------------------------------------
def _report(code: str) -> str:
    """세 제목과 닫힌 코드 블록을 갖춘 최소 리뷰 답변을 만든다(제목·문법 검사는 통과하는 형태)."""
    return "\n".join(HEADINGS) + "\n```python\n" + code + "\n```"


@pytest.fixture
def fake_root(tmp_path):
    """harness 패키지만 있고 오타 패키지 harnessx는 없는 저장소 구조를 흉내 낸다."""
    tools = tmp_path / "harness/mcp/tools"
    tools.mkdir(parents=True)
    (tools / "multi_persona_tools.py").write_text("X = 1\n", encoding="utf-8")
    (tools / "execution_tools.py").write_text("Y = 1\n", encoding="utf-8")
    return tmp_path


ORIGINAL = (
    "from harness.mcp.tools.execution_tools import Y\n"
    "def launch():\n"
    "    return ['-m', 'harness.mcp.tools.multi_persona_tools']\n"
)


# ---------------------------------------------------------------------------
# 1) import 실존 검사 — 실제 사고 재현
# ---------------------------------------------------------------------------
def test_reproduce_wrong_module_rename_is_rejected(fake_root):
    """실제 사고 유형: 실제 `-m` 모듈을 존재하지 않는 패키지 이름으로 바꾸면 오류여야 한다."""
    query = build_review_query("sample.py", ORIGINAL)
    broken = ORIGINAL.replace("'harness.mcp", "'harnessx.mcp")
    errors = validate_review(_report(broken), query, search_roots=[fake_root])
    assert any("harnessx.mcp.tools.multi_persona_tools" in e for e in errors), errors


def test_unchanged_resolvable_source_passes(fake_root):
    """원본과 같은(실존하는) import만 있으면 새 검사가 오류를 만들지 않는다."""
    query = build_review_query("sample.py", ORIGINAL)
    assert validate_review(_report(ORIGINAL), query, search_roots=[fake_root]) == []


def test_new_missing_import_statement_is_rejected(fake_root):
    """잘못된 입력: 제안 소스가 존재하지 않는 패키지를 새로 import하면 오류."""
    query = build_review_query("sample.py", ORIGINAL)
    broken = "import no_such_package_20261102\n" + ORIGINAL
    errors = validate_review(_report(broken), query, search_roots=[fake_root])
    assert any("no_such_package_20261102" in e for e in errors), errors


def test_stdlib_and_relative_imports_are_not_flagged(fake_root):
    """표준 라이브러리와 상대 import는 실존 검사 대상에서 오판하지 않는다."""
    query = build_review_query("sample.py", ORIGINAL)
    code = "import os.path\nimport json\nfrom . import sibling\n" + ORIGINAL
    assert validate_review(_report(code), query, search_roots=[fake_root]) == []


def test_import_missing_in_original_too_is_not_new_breakage(fake_root):
    """원본에서도 해석되지 않던 모듈(선택 의존성 등)은 제안 탓이 아니므로 오류로 만들지 않는다."""
    original = "import optional_dep_absent\n" + ORIGINAL
    query = build_review_query("sample.py", original)
    assert validate_review(_report(original), query, search_roots=[fake_root]) == []


# ---------------------------------------------------------------------------
# 2) model_verified 내용 판단
# ---------------------------------------------------------------------------
GOOD_OUTPUT = "[출력 검증] 오류=[], 보고서=x\n[최종 검증된 답변]:\n본문"


def test_verified_requires_all_three_conditions(tmp_path):
    proposed = tmp_path / "proposed.py"
    proposed.write_text("X = 1\n", encoding="utf-8")
    ok, reasons = review._judge_verification(GOOD_OUTPUT, proposed)
    assert ok is True and reasons == []


@pytest.mark.parametrize("text,make_file,reason", [
    # LLM verifier 미통과(초안 대체 답변)
    ("[출력 검증] 오류=[], 보고서=x\n[검증 미완료 - 초안 대체 답변]:\n", True, "verifier"),
    # 출력 계약 오류(예: import 실존 실패) — 마커가 있어도 계약 오류면 불합격
    ("[출력 검증] 오류=['존재하지 않는 import 대상: a.b'], 보고서=x\n[최종 검증된 답변]:\n", True, "계약"),
    # 제안 소스 파일 미생성
    (GOOD_OUTPUT, False, "제안"),
    # 잘못된 입력: 빈 출력
    ("", True, "verifier"),
])
def test_verified_false_with_reason(tmp_path, text, make_file, reason):
    proposed = tmp_path / "proposed.py"
    if make_file:
        proposed.write_text("X = 1\n", encoding="utf-8")
    ok, reasons = review._judge_verification(text, proposed)
    assert ok is False
    assert any(reason in r for r in reasons), reasons


# ---------------------------------------------------------------------------
# 3) 제안 파일 충돌 방지 — job 전용 출력 폴더
# ---------------------------------------------------------------------------
def test_review_command_writes_into_job_folder():
    """dry-run 계획의 리뷰 명령에 job 전용 --output-dir가 들어가고, job마다 다르다."""
    target = "FastAPI/LangGraph/multi_persona/review_contract.py"
    first = asyncio.run(review.review_python_source(target))
    second = asyncio.run(review.review_python_source(target))
    for plan in (first, second):
        assert "--output-dir" in plan["review_command"]
        out_dir = plan["review_command"][plan["review_command"].index("--output-dir") + 1]
        assert out_dir.endswith("job_" + plan["job_id"])
    assert first["job_id"] != second["job_id"]
    assert first["executed"] is False and second["executed"] is False


# ---------------------------------------------------------------------------
# 4) 시간 정책 — 리뷰 3590 + 여유 10 <= 유닛 상한 3600
# ---------------------------------------------------------------------------
def test_review_budget_fits_unit_cap():
    assert config.MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS == 3590
    assert config.SPS_GENERAL_UNIT_RUNTIME_SECONDS == 3600
    assert (config.MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS + config.SPS_WORKER_RESULT_GRACE_SECONDS
            <= config.SPS_GENERAL_UNIT_RUNTIME_SECONDS)
    plan = asyncio.run(review.review_python_source("FastAPI/LangGraph/multi_persona/review_contract.py"))
    assert plan["timeout_seconds"] == 3590
    assert "RuntimeMaxSec=3600" in plan["command"]


# ---------------------------------------------------------------------------
# 5) 결과 없이 끝난 워커 — 실패를 result.json에 영구 기록
# ---------------------------------------------------------------------------
class _FakeProcess:
    """systemctl show 응답을 흉내 내는 대역(실제 systemd 호출 없음)."""
    returncode = 0

    async def communicate(self):
        return b"LoadState=not-found\nActiveState=inactive\nResult=timeout\n", b""


def test_lost_worker_failure_is_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    source = tmp_path / "sample.py"
    source.write_text("X = 1\n", encoding="utf-8")
    job_id = "a" * 32
    request_path, result_path = review._job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({"source_path": "sample.py", "unit": "u", "started_at": 0}),
                            encoding="utf-8")

    async def fake_exec(*args, **kwargs):
        return _FakeProcess()

    monkeypatch.setattr(review.asyncio, "create_subprocess_exec", fake_exec)
    state = asyncio.run(review._review_status(source, job_id))
    assert state["state"] == "failed" and state["success"] is False
    # 실패가 파일로 남아, 이후 조회는 systemctl 없이도 같은 실패를 돌려준다.
    assert result_path.is_file()
    assert json.loads(result_path.read_text(encoding="utf-8"))["state"] == "failed"


def test_bad_job_id_still_rejected():
    """잘못된 입력: 경로 탈출 job_id는 디스크 접근 전에 거부한다(기존 동작 유지)."""
    with pytest.raises(ValueError):
        review._job_files("../escape")


# ---------------------------------------------------------------------------
# 6) 재현(job b7d1de9f, 2026-11-02): LLM 호출이 전부 403으로 실패했는데
#    CLI가 returncode 0으로 끝나 state=completed, success=true로 보고되었다.
#    리뷰 성공은 '검증된 제안 생성'이어야 하므로 success=false, state=failed여야 한다.
# ---------------------------------------------------------------------------
def test_unverified_review_is_not_success(tmp_path, monkeypatch):
    import hashlib
    from types import SimpleNamespace

    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    source = tmp_path / "sample.py"
    source.write_text("X = 1\n", encoding="utf-8")
    job_id = "b" * 32
    request_path, result_path = review._job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({
        "source_path": "sample.py", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "timeout_seconds": 60, "output_limit": 1000, "error_path": None}), encoding="utf-8")
    # 실제 사고 출력 형태: 계약 오류 + 초안 대체 답변, 제안 파일 없음 (LLM·대상 소스 실행 없음)
    failed_output = ("[출력 검증] 오류=['누락 제목: ## 1.'], 보고서=x\n"
                     "[검증 미완료 - 초안 대체 답변]:\n[시스템 경고] API 인증 실패\n")
    monkeypatch.setattr(review.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout=failed_output.encode(), stderr=b""))
    review._run_review_job(job_id)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["process_completed"] is True      # 프로세스 자체는 정상 종료
    assert result["success"] is False                # 리뷰로서는 실패
    assert result["state"] == "failed"
    assert result["model_verified"] is False and len(result["verification_reasons"]) == 3
