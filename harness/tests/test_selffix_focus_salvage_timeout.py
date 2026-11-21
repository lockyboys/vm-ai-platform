"""스스로 고치는 앱 개선 3가지 테스트 (2026-11-21, LuckyBoys 승인: '실패 테스트 집중·추가 기능 차단·느린 모델 시간 배분').

사고(메모리 에이전트 자가 수정, Ollama gemma4:e4b·12b 4회 시험)
① 1라운드 AI는 어떤 테스트가 이미 실패하는지 몰라, 핵심 결함(약관 검색어)을 4번 모두 못 고쳤다.
② 결함과 무관한 함수(Gmail 호출 방식·검증 노드 등)까지 바꿔 통과하던 테스트를 1~3개씩 깨뜨려 전부 되돌려졌다.
③ 12b는 한 라운드에 30~45분이 걸려 작업 한도(3590초)에 2라운드도 다 못 끝냈다.
기대
① 1라운드 전에 원본으로 테스트를 돌려, 실패 테스트(이름·메시지·테스트 코드 일부)를 focus.txt로 만들어 --error-path로 준다.
② 제안이 퇴행을 내면 바뀐 함수·클래스를 하나씩 원본으로 되돌려 보고, 퇴행이 사라지고 통과가 늘면 그 상태로 반영한다.
   판정 규칙(퇴행 0 + 통과 수 증가)은 그대로다.
③ config 공급자 항목의 job_timeout_seconds로 공급자별 작업 한도를 둔다(없으면 기존 3590초).
LLM·systemd·실제 pytest는 실행하지 않는다(subprocess.run 대역).
"""
import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest

from harness.mcp.tools import auto_apply
from harness.mcp.tools import multi_persona_tools as review
from harness.tests.test_review_feedback_rounds import FIRST, GOOD, ORIGINAL, fake_run, result


# ---------------------------------------------------------------- 공통: 임시 job 만들기
def _make_job(tmp_path, monkeypatch, content, error_path=None, timeout=600):
    """임시 저장소에 원본·테스트·request.json을 만든다(내용·오류 로그·작업 한도를 바꿔 쓸 수 있게)."""
    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    source = tmp_path / "sample.py"
    source.write_text(content, encoding="utf-8")
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "tests/test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    job_id = "e" * 32
    request_path, _ = review._job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({
        "source_path": "sample.py", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "timeout_seconds": timeout, "output_limit": 1000, "error_path": error_path,
        "auto_apply": True, "test_paths": ["tests/test_sample.py"]}), encoding="utf-8")
    return source, job_id


def _patch(monkeypatch, run):
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)


def _error_path(command):
    return command[command.index("--error-path") + 1] if "--error-path" in command else None


# ---------------------------------------------------------------- ① 실패 테스트 집중
def test_reproduce_first_round_gets_failing_tests(tmp_path, monkeypatch):
    """재현: 원본에서 이미 실패하는 테스트가 1라운드 리뷰의 --error-path(focus.txt)로 전달된다."""
    source, job_id = _make_job(tmp_path, monkeypatch, ORIGINAL)
    run = fake_run(source, [GOOD, GOOD])
    _patch(monkeypatch, run)
    review._run_review_job(job_id)
    first = run.calls["review"][0]
    focus = _error_path(first)
    assert focus and focus.endswith("focus.txt")
    text = review.Path(focus).read_text(encoding="utf-8")
    assert "먼저 고칠" in text and "test_ok" in text and "keep() -> 2, 기대 3" in text
    assert source.read_text(encoding="utf-8") == GOOD          # 이후 흐름은 그대로(반영됨)


def test_no_focus_when_original_passes(tmp_path, monkeypatch):
    """원본 테스트가 모두 통과하면 focus.txt를 만들지 않는다(1라운드 명령은 예전 그대로)."""
    source, job_id = _make_job(tmp_path, monkeypatch, GOOD)
    run = fake_run(source, [GOOD])
    _patch(monkeypatch, run)
    review._run_review_job(job_id)
    assert _error_path(run.calls["review"][0]) is None


def test_user_error_log_is_kept_inside_focus(tmp_path, monkeypatch):
    """사용자가 준 오류 로그(error_path)는 버리지 않고 focus.txt 뒤에 붙인다."""
    (tmp_path / "err.log").write_text("사용자 오류 로그 줄", encoding="utf-8")
    source, job_id = _make_job(tmp_path, monkeypatch, ORIGINAL, error_path="err.log")
    run = fake_run(source, [GOOD])
    _patch(monkeypatch, run)
    review._run_review_job(job_id)
    text = review.Path(_error_path(run.calls["review"][0])).read_text(encoding="utf-8")
    assert "먼저 고칠" in text and "사용자 오류 로그 줄" in text


PYTEST_TEXT = (
    "harness/tests/x.py:257: in test\n"
    "    fn(target, monkeypatch)\n"
    "_ _ _ _ _ _ _ _\n"
    "    def case_rag(target, monkeypatch):\n"
    "        agent = load_agent(target, monkeypatch)\n"
    "        state = {\"messages\": [HumanMessage(content=\"발목 골절\"), ToolMessage(content=\"메일\")]}\n"
    "        agent.agent_node(state)\n"
    ">       assert seen == [\"발목 골절\"]\n"
    "E       AssertionError\n"
    "harness/tests/x.py:235: AssertionError\n"
)


def test_failure_context_shows_test_code_before_assert():
    """실패 테스트의 코드(assert 앞 줄들)와 E 줄을 보여 준다 = AI가 무엇을 기대하는지 안다."""
    lines = review._failure_context(PYTEST_TEXT, 12)
    joined = "\n".join(lines)
    assert "ToolMessage" in joined and 'assert seen == ["발목 골절"]' in joined and "AssertionError" in joined
    assert "fn(target, monkeypatch)" not in joined             # 감싼 함수(바깥 프레임)는 빼고 가장 안쪽만


@pytest.mark.parametrize("text, limit", [(None, 12), ("", 12), ("아무 표시 없는 글\n", 12), (PYTEST_TEXT, 0)])
def test_failure_context_bad_input_is_empty(text, limit):
    """잘못된 입력: 본문 없음·표시 줄 없음·줄 수 0 이하 → 예외 없이 빈 목록."""
    assert review._failure_context(text, limit) == []


# ---------------------------------------------------------------- ② 추가 기능 차단(함수 단위 되돌림)
ORIG = "def a():\n    return 'bug'\n\n\ndef b():\n    return 'keep'\n"
PROP_FIX_AND_BREAK = "def a():\n    return 'fixed'\n\n\ndef b():\n    return 'changed'\n"   # a 고침 + b 망가뜨림
PROP_BREAK_ONLY = "def a():\n    return 'bug'\n\n\ndef b():\n    return 'changed'\n"       # b만 망가뜨림


def _fake_pytest(source):
    """pytest 대역: test_a는 a가 고쳐졌을 때, test_b는 b가 원래대로일 때 통과(junit xml도 쓴다)."""
    calls = {"pytest": 0}

    def run(command, **_kwargs):
        calls["pytest"] += 1
        text = source.read_text(encoding="utf-8")
        cases = {"test_a": "return 'fixed'" in text, "test_b": "return 'keep'" in text}
        body = "".join(f'<testcase classname="t" name="{n}">' + ("" if ok else '<failure message="x"/>')
                       + "</testcase>" for n, ok in cases.items())
        xml = next(a for a in command if a.startswith("--junitxml=")).split("=", 1)[1]
        auto_apply.Path(xml).write_text(f"<testsuite>{body}</testsuite>", encoding="utf-8")
        return SimpleNamespace(returncode=0 if all(cases.values()) else 1, stdout=b"pytest", stderr=b"")

    run.calls = calls
    return run


def _apply(tmp_path, monkeypatch, original, proposal):
    source = tmp_path / "m.py"
    source.write_text(original, encoding="utf-8")
    proposed = tmp_path / "proposed.py"
    proposed.write_text(proposal, encoding="utf-8")
    run = _fake_pytest(source)
    monkeypatch.setattr(auto_apply.subprocess, "run", run)
    state = auto_apply.apply_with_rollback(
        source, proposed, tmp_path, hashlib.sha256(source.read_bytes()).hexdigest(),
        ["tests/test_m.py"], 600, tmp_path, policy="improve")
    return source, state, run


def test_reproduce_revert_unrelated_change_keeps_fix(tmp_path, monkeypatch):
    """재현: a는 고치고 b를 망가뜨린 제안 → b만 원본으로 되돌려 반영(예전에는 전부 되돌림)."""
    source, state, _ = _apply(tmp_path, monkeypatch, ORIG, PROP_FIX_AND_BREAK)
    assert state["applied"] is True and state["rolled_back"] is False
    assert state["reverted_functions"] == ["b"]
    assert source.read_text(encoding="utf-8") == "def a():\n    return 'fixed'\n\n\ndef b():\n    return 'keep'\n"
    assert state["tests_passed_after"] == 2 and not state.get("newly_failed")


def test_revert_without_gain_still_rolls_back(tmp_path, monkeypatch):
    """되돌려서 퇴행은 사라져도 통과가 늘지 않으면(좋아진 게 없음) 기존 규칙대로 전부 되돌린다."""
    source, state, _ = _apply(tmp_path, monkeypatch, ORIG, PROP_BREAK_ONLY)
    assert state["rolled_back"] is True and state["applied"] is False
    assert source.read_text(encoding="utf-8") == ORIG


@pytest.mark.parametrize("bad_max", [0, -1, "x", True])
def test_bad_revert_limit_means_no_salvage(tmp_path, monkeypatch, bad_max):
    """잘못된 입력·끔: 되돌림 최대 개수가 0 이하·숫자 아님·bool이면 되돌림을 시도하지 않고 예전처럼 되돌린다."""
    monkeypatch.setattr(auto_apply.project_config, "MULTI_PERSONA_AUTO_APPLY_REVERT_MAX_FUNCTIONS", bad_max)
    source, state, run = _apply(tmp_path, monkeypatch, ORIG, PROP_FIX_AND_BREAK)
    assert state["rolled_back"] is True and source.read_text(encoding="utf-8") == ORIG
    assert run.calls["pytest"] == 2                            # 기준선 + 제안 1번뿐(되돌림 시험 없음)


# ---------------------------------------------------------------- ③ 공급자별 작업 한도
def _providers(monkeypatch, value):
    providers = {name: dict(entry) for name, entry in review.project_config.MULTI_PERSONA_REVIEW_PROVIDERS.items()}
    providers["ollama"]["job_timeout_seconds"] = value
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_REVIEW_PROVIDERS", providers)


def _plan(provider):
    return asyncio.run(review.review_python_source("harness/mcp/tools/auto_apply.py", provider=provider, dry_run=True))


def test_reproduce_ollama_gets_its_own_job_timeout(monkeypatch):
    """재현: ollama에 job_timeout_seconds가 있으면 그 값이 작업 한도와 systemd 상한(+결과 저장 여유)이 된다."""
    _providers(monkeypatch, 10800)
    plan = _plan("ollama")
    grace = int(review.project_config.SPS_WORKER_RESULT_GRACE_SECONDS)
    assert plan["timeout_seconds"] == 10800
    assert f"RuntimeMaxSec={10800 + grace}" in plan["command"]


def test_provider_without_job_timeout_keeps_default(monkeypatch):
    """값이 없는 공급자(gemini 등)는 예전 한도 그대로."""
    _providers(monkeypatch, 10800)
    plan = _plan("gemini")
    assert plan["timeout_seconds"] == int(review.project_config.MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS)


@pytest.mark.parametrize("bad", [0, -5, True, "10800", 10 ** 9])
def test_bad_job_timeout_is_rejected(monkeypatch, bad):
    """잘못된 입력: 0 이하·bool·문자열·상한 초과 값은 작업을 시작하기 전에 거부한다."""
    _providers(monkeypatch, bad)
    with pytest.raises(ValueError):
        _plan("ollama")


def test_worker_accepts_long_provider_timeout(tmp_path, monkeypatch):
    """워커도 공급자 한도(예: 10800초)를 '잘못된 한도'로 거부하지 않고 끝까지 처리한다."""
    source, job_id = _make_job(tmp_path, monkeypatch, ORIGINAL, timeout=10800)
    _patch(monkeypatch, fake_run(source, [GOOD, GOOD]))
    review._run_review_job(job_id)
    data = result(job_id)
    assert "Invalid review timeout" not in (data.get("stderr") or "")
    assert source.read_text(encoding="utf-8") == GOOD
