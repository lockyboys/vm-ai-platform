"""블라인드 리뷰 지시문 선택(prompt_variant) 검증 (2026-11-01, LuckyBoys: 버그 집중형 재실험).

규칙:
  - 지시문은 config.BLIND_REVIEW_PROMPTS 에서 고른다. 'review'는 기존 문구 그대로(Gemini 80/82, gemma 27/82 기준선).
  - 새 지시문 'bug_focus'에는 문제별 힌트(범주명·앱 이름·문제 수)가 들어가면 안 된다(82건 공통 문구).
  - submit(prompt_variant=...)는 워커 stdin에 지시문 종류를 넘기고 request.json에 기록한다. 기본값은 'review'.
  - 이어서 실행(resume)은 이전 지시문을 그대로 쓰고, 다른 지시문을 주면 거부한다(한 job 안에서 지시문 혼합 금지).
  - 잘못된 지시문 이름은 프로세스를 띄우기 전에 거부한다.
"""
import importlib.util
import json
from pathlib import Path

import pytest

import config
from harness.mcp.tools import blind_review_jobs_v2 as jobs

# 워커는 패키지가 아니므로 파일 경로로 로드(main()은 실행되지 않음) — 기존 gate 테스트와 같은 방식
_spec = importlib.util.spec_from_file_location(
    "blind_worker_prompt_test", Path(config.PROJECT_ROOT) / "harness/apps/blind_review_20261027/blind_worker.py")
worker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(worker)

OLD = "b" * 32


# ───────────── 설정·워커 ─────────────

def test_review_prompt_is_unchanged_baseline():
    """기존 결과와 비교하려면 'review' 문구가 글자 하나 바뀌면 안 된다."""
    assert config.BLIND_REVIEW_PROMPTS["review"] == "이 프로그램을 검토해 주세요."


def test_bug_focus_prompt_has_no_item_hints():
    """문제별 힌트(범주·앱·문제 수)를 주면 블라인드가 깨진다."""
    text = config.BLIND_REVIEW_PROMPTS["bug_focus"]
    assert "버그" in text and "위치" in text and "원인" in text
    for hint in ("syntax", "runtime", "performance", "logic", "문법", "성능", "논리",
                 "계산기", "테트리스", "tetris", "calculator", "82"):
        assert hint not in text.lower()


def test_checklist_prompt_is_generic_four_point_review():
    """2026-11-01 LuckyBoys '4관점 점검표': 문법 6/20 원인(결함 미언급) 대응 실험.
    82건 공통 문구 — 구문·실행 예외·느린 부분·틀린 결과 4가지를 같은 무게로 묻고,
    범주 이름(문법·성능·논리 등)·앱 이름·문제 수는 넣지 않는다(블라인드 유지)."""
    text = config.BLIND_REVIEW_PROMPTS["checklist"]
    for step in ("①", "②", "③", "④"):
        assert step in text  # 4관점이 모두 들어 있어야 함
    assert "위치" in text and "원인" in text and "문제 없음" in text
    for hint in ("syntax", "runtime", "performance", "logic", "문법", "성능", "논리",
                 "계산기", "테트리스", "tetris", "calculator", "82"):
        assert hint not in text.lower()
    # 기존 기준선 문구는 그대로여야 한다(이전 결과와 비교 가능)
    assert config.BLIND_REVIEW_PROMPTS["review"] == "이 프로그램을 검토해 주세요."


def test_checklist_rules_prompt_adds_generic_convention_step():
    """2026-11-01 LuckyBoys 선택 A: 12b 점검표 논리 13/20 — 놓친 7건 중 6건이 테트리스(점수·레벨 규칙 4건).
    점검표 ①~④는 그대로 두고 ⑤ '표준 규칙·관례와 다르게 동작하는 부분'만 추가한다(효과를 ⑤ 하나로 분리).
    앱 종류가 드러나는 단어(게임·계산·점수 등)는 넣지 않는다 — 82건 공통 문구, 블라인드 유지."""
    base = config.BLIND_REVIEW_PROMPTS["checklist"]
    text = config.BLIND_REVIEW_PROMPTS["checklist_rules"]
    assert "⑤" in text and "규칙" in text and "관례" in text
    # ①~④ 문구는 checklist 와 같아야 비교가 공정하다(⑤ 앞부분이 동일)
    assert text.split("⑤")[0] == base.split(" 부분을 차례로")[0] + " 부분 "
    for hint in ("syntax", "runtime", "performance", "logic", "문법", "성능", "논리",
                 "계산기", "테트리스", "tetris", "calculator", "82", "게임", "계산", "점수", "레벨"):
        assert hint not in text.lower()
    assert config.BLIND_REVIEW_PROMPTS["checklist"] == base  # 기존 점검표 문구 보존


@pytest.mark.parametrize("variant", ["review", "bug_focus", "checklist", "checklist_rules"])
def test_worker_resolves_configured_prompt(variant):
    assert worker.resolve_prompt(variant) == config.BLIND_REVIEW_PROMPTS[variant]


@pytest.mark.parametrize("bad", ["", "unknown", "REVIEW", None, 1, ["review"]])
def test_worker_rejects_unknown_prompt(bad):
    with pytest.raises(ValueError):
        worker.resolve_prompt(bad)


# ───────────── 제출 도구 ─────────────

@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "JOB_ROOT", tmp_path)
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            self.pid = 777
            self.sent = []
            self.stdin = type("S", (), {"write": lambda s, d: self.sent.append(d), "close": lambda s: None})()
            calls.append(self)

    monkeypatch.setattr(jobs.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(jobs, "_alive", lambda pid: False)
    return tmp_path, calls


def _sent(call):
    return json.loads(b"".join(call.sent).decode())


def test_default_variant_is_review(env):
    root, calls = env
    req = jobs.submit("ollama")
    assert _sent(calls[0])["prompt_variant"] == "review"
    assert json.loads((root / req["job_id"] / "request.json").read_text())["prompt_variant"] == "review"


def test_bug_focus_is_passed_to_worker(env):
    root, calls = env
    req = jobs.submit("ollama", prompt_variant="bug_focus")
    # 2026-11-01: ollama 제출은 실행 대상·모델도 넘긴다(기본 laptop + config.OLLAMA_MODEL)
    assert _sent(calls[0]) == {"provider": "ollama", "job_id": req["job_id"], "prompt_variant": "bug_focus",
                               "ollama_target": "laptop", "ollama_model": config.OLLAMA_MODEL}
    assert req["prompt_variant"] == "bug_focus"


# 빈 값("")·None은 MCP에서 '지정 안 함'이므로 거부 대상이 아니다(기본값 review로 처리 — test_default_variant_is_review).
@pytest.mark.parametrize("bad", ["unknown", "REVIEW", 3, 0])
def test_unknown_variant_rejected_before_launch(env, bad):
    _, calls = env
    with pytest.raises(ValueError):
        jobs.submit("ollama", prompt_variant=bad)
    assert calls == []


def _old_job(root, variant):
    d = root / OLD
    d.mkdir()
    req = {"job_id": OLD, "provider": "ollama", "pid": 1}
    if variant is not None:
        req["prompt_variant"] = variant
    (d / "request.json").write_text(json.dumps(req), encoding="utf-8")


def test_resume_keeps_previous_variant(env):
    root, calls = env
    _old_job(root, "bug_focus")
    jobs.submit("ollama", resume_job_id=OLD)
    assert _sent(calls[0])["prompt_variant"] == "bug_focus"


def test_resume_of_legacy_job_uses_review(env):
    """prompt_variant 기록이 없는 예전 job은 기존 문구('review')로 만든 것이다."""
    root, calls = env
    _old_job(root, None)
    jobs.submit("ollama", resume_job_id=OLD)
    assert _sent(calls[0])["prompt_variant"] == "review"


def test_resume_with_different_variant_rejected(env):
    root, calls = env
    _old_job(root, "review")
    with pytest.raises(ValueError, match="prompt_variant"):
        jobs.submit("ollama", resume_job_id=OLD, prompt_variant="bug_focus")
    assert calls == []
