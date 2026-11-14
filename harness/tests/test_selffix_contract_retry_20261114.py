"""2차 수정안이 출력 검사 오탐으로 버려진 사고 재현 테스트 (2026-11-14, LuckyBoys 요청).

사고(job ca0a8c65, 테트리스 오류 20개, Gemini)
- 2차 답은 text_to_board를 split('\\n')으로 바르게 고쳤는데, 출력 검사(review_contract.validate_review)가
  "진단된 함수 수정 미반영: board_to_text, clear_lines, ..."로 거부했다.
  원인 1: 진단에 `text_to_board(text)`처럼 괄호까지 백틱에 넣어 적어 함수 이름으로 인식하지 못했다.
  원인 2: 수정 대상을 하나도 못 찾으면 '언급된 함수 중 하나는 바뀌어야 함'으로 검사하는데,
          '### [수정 불필요 대상]' 절에 적힌 함수까지 언급으로 셌다.
- 앱(_run_feedback_rounds)은 검사에서 떨어지면 바로 멈춰, 같은 라운드를 다시 시도하지 않았다.
기대
- 검사: 괄호 표기도 함수로 인식, '수정 불필요' 절의 함수는 대상·언급에서 제외, '수정 대상' 절의 머리 줄 함수는 대상.
- 앱: 검사에서 떨어지면 거부 이유를 피드백에 넣어 같은 라운드를 정해진 횟수만큼 다시 시도한다.
LLM·systemd는 실행하지 않는다(subprocess.run 대역).
"""
import hashlib
import json
from types import SimpleNamespace

import pytest

from FastAPI.LangGraph.multi_persona.review_contract import HEADINGS, build_review_query, validate_review
from harness.mcp.tools import multi_persona_tools as review

# ------------------------------------------------------------------ 1) 출력 검사(review_contract)
ORIGINAL_SRC = (
    "def board_to_text(board):\n    return '\\n'.join(board)\n\n"
    "def text_to_board(text):\n    return text.splitlines()\n\n"
    "def place(board):\n    return board\n"
)
FIXED_SRC = ORIGINAL_SRC.replace("return text.splitlines()", "return text.split('\\n')")
QUERY = build_review_query("tetris.py", ORIGINAL_SRC)
# 실제 2차 답(round2/review_output.txt)의 진단 구조를 줄인 것
DIAGNOSIS = (
    "### [수정 대상]\n"
    "- **`text_to_board(text)` (위험도: High — 테스트 실패 직접 유발)**\n"
    "  - **진단 및 재현 조건**: `text_to_board('#.\\n')` 호출 시 끝 개행이 무시됩니다.\n"
    "  - **수정 근거**: `board_to_text`는 끝에 개행을 붙이지 않으므로 split('\\n')을 써야 합니다.\n"
    "\n"
    "### [수정 불필요 대상 (진단 통과 및 유지)]\n"
    "- **`place`, `board_to_text` (위험도: Low)**: 계약을 정확히 준수하고 있습니다.\n"
)


def _report(diagnosis, code):
    return (HEADINGS[0] + "\n평가\n" + HEADINGS[1] + "\n" + diagnosis + "\n"
            + HEADINGS[2] + "\n```python\n" + code + "\n```")


def test_reproduce_fix_section_with_call_form_passes():
    """재현: 수정 대상 절의 `text_to_board(text)`만 고쳤으면 통과해야 한다(사고 때는 거부됨)."""
    assert validate_review(_report(DIAGNOSIS, FIXED_SRC), QUERY) == []


def test_fix_section_target_not_changed_is_rejected():
    """잘못된 입력: 수정 대상이라고 해 놓고 안 고쳤으면 여전히 거부하고, 그 함수 이름을 알려 준다."""
    errors = validate_review(_report(DIAGNOSIS, ORIGINAL_SRC), QUERY)
    assert any("text_to_board" in e for e in errors)
    assert not any("place" in e or "board_to_text" in e for e in errors)  # 수정 불필요 절은 탓하지 않음


def test_no_fix_section_only_and_nothing_changed_passes():
    """모든 함수를 '수정 불필요' 절에만 적고 아무것도 안 바꿨으면 거부할 이유가 없다."""
    diagnosis = "### [수정 불필요 대상]\n- **`place`, `board_to_text`, `text_to_board`**: 문제 없음.\n"
    assert validate_review(_report(diagnosis, ORIGINAL_SRC), QUERY) == []


def test_plain_mention_fallback_rule_kept():
    """기존 규칙 유지: 절 표시가 없고 수정 표시도 없으면 언급된 함수 중 하나는 바뀌어야 한다."""
    diagnosis = "- `text_to_board`가 끝 개행을 무시한다.\n"
    assert validate_review(_report(diagnosis, FIXED_SRC), QUERY) == []
    assert validate_review(_report(diagnosis, ORIGINAL_SRC), QUERY)


# ------------------------------------------------------------------ 2) 앱의 재시도(_run_feedback_rounds)
ORIGINAL = "def keep():\n    return 1\n"
FIRST = "def keep():\n    return 2\n"   # 1차 수정안(테스트 실패)
GOOD = "def keep():\n    return 3\n"    # 다음 수정안(테스트 통과)
VERIFIED = "[출력 검증] 오류=[], 보고서=x\n[최종 검증된 답변]:\n본문\n"
REJECTED = ("[출력 검증] 오류=['진단된 함수 수정 미반영: place'], 보고서=x\n"
            "[검증 미완료 - 초안 대체 답변]:\n")


@pytest.fixture
def job(tmp_path, monkeypatch):
    """임시 저장소에 원본·테스트·request.json을 만든다."""
    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    source = tmp_path / "sample.py"
    source.write_text(ORIGINAL, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    job_id = "e" * 32
    request_path, _ = review._job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({
        "source_path": "sample.py", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "timeout_seconds": 600, "output_limit": 1000, "error_path": None,
        "auto_apply": True, "test_paths": ["tests/test_sample.py"]}), encoding="utf-8")
    return source, job_id


def fake_run(source, proposals, verified):
    """리뷰 CLI는 proposals를 차례로 내고(verified가 False면 검사 거부 출력), pytest는 원본이 GOOD일 때만 통과."""
    calls = {"review": []}

    def run(command, **_kwargs):
        if "pytest" in command:
            ok = source.read_text(encoding="utf-8") == GOOD
            xml = next(arg for arg in command if arg.startswith("--junitxml=")).split("=", 1)[1]
            body = "" if ok else '<failure message="keep() -&gt; 2, 기대 3"/>'
            review.Path(xml).write_text(f'<testsuite><testcase classname="t" name="test_ok">{body}</testcase></testsuite>',
                                        encoding="utf-8")
            return SimpleNamespace(returncode=0 if ok else 1, stdout=b"pytest", stderr=b"")
        number = len(calls["review"])
        calls["review"].append(command)
        out_dir = review.Path(command[command.index("--output-dir") + 1])
        if verified[number]:
            (out_dir / "proposed.py").write_text(proposals[number], encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout=(VERIFIED if verified[number] else REJECTED).encode(), stderr=b"")

    run.calls = calls
    return run


def _run(job, monkeypatch, proposals, verified):
    source, job_id = job
    run = fake_run(source, proposals, verified)
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)
    review._run_review_job(job_id)
    return run, json.loads(review._job_files(job_id)[1].read_text(encoding="utf-8"))


def test_reproduce_rejected_round_is_retried_and_applied(job, monkeypatch):
    """재현: 2차가 검사에서 거부되면 거부 이유를 피드백에 넣어 같은 라운드를 다시 시도하고, 통과하면 반영한다."""
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES", 1)
    run, data = _run(job, monkeypatch, [FIRST, GOOD, GOOD], (True, False, True))
    source, job_id = job
    assert source.read_text(encoding="utf-8") == GOOD
    assert len(run.calls["review"]) == 3
    rounds = data["auto_apply_rounds"]
    assert [(r["round"], r.get("attempt", 0), r["verified"]) for r in rounds] == [(1, 0, True), (2, 0, False), (2, 1, True)]
    retry_dir = review._job_files(job_id)[0].parent / "round2_retry1"
    feedback = (retry_dir / "feedback.txt").read_text(encoding="utf-8")
    assert "진단된 함수 수정 미반영: place" in feedback   # 거부 이유가 AI에게 전달됨
    assert "keep() -> 2, 기대 3" in feedback             # 원래 실패 테스트도 그대로 전달됨
    assert data["final_proposed_path"].endswith("round2_retry1/proposed.py")


def test_retry_limit_keeps_original(job, monkeypatch):
    """잘못된 결과가 계속되면 정해진 횟수만 다시 시도하고 멈춘다(원본 유지, 무한 반복 없음)."""
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES", 1)
    run, data = _run(job, monkeypatch, [FIRST, GOOD, GOOD], (True, False, False))
    source, _ = job
    assert source.read_text(encoding="utf-8") == ORIGINAL
    assert len(run.calls["review"]) == 3
    assert data["auto_apply_rounds"][-1]["verified"] is False


@pytest.mark.parametrize("bad", [0, -1])
def test_zero_or_invalid_retries_means_no_extra_call(job, monkeypatch, bad):
    """잘못된 입력·0 설정: 다시 시도 횟수가 0 이하이면 예전처럼 바로 멈춘다."""
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES", bad)
    run, _data = _run(job, monkeypatch, [FIRST, GOOD, GOOD], (True, False, True))
    assert len(run.calls["review"]) == 2
