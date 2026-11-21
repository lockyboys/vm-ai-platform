"""스스로 고치는 앱 '상황별 대응표 + 고쳐질 때까지 반복' 테스트 (2026-11-21, LuckyBoys 요청).

요청
- "수정 중 어떤 상황을 만나면 어떻게 하는지 로직으로" → config.MULTI_PERSONA_SELFFIX_ACTIONS 대응표 하나로
  상황(all_passed·improved·no_gain·regressed·format_rejected·cli_error·provider_fatal·review_timeout·time_low)마다
  다음 행동(stop·next_round·retry_same_round)을 정하고, 코드는 그 표대로만 움직인다.
- "고쳐질 때까지 반복" → 전부 통과하면 성공 종료, config.MULTI_PERSONA_SELFFIX_STAGNATION_ROUNDS 라운드 연속
  통과 수가 늘지 않으면(제자리걸음) 멈춘다. 최대 라운드(config.MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS)는 안전 상한일 뿐이다.
사고: 예전에는 3라운드에서 무조건 끝나, 조금씩 나아지던 수정도 중간에 멈췄다(메모리 에이전트·Ollama).
LLM·systemd·실제 pytest는 실행하지 않는다(subprocess.run 대역).
"""
import hashlib
import json
from types import SimpleNamespace

import pytest

from harness.mcp.tools import multi_persona_tools as review

VERIFIED = "[출력 검증] 오류=[], 보고서=x\n[최종 검증된 답변]:\n본문\n"
REJECTED = "[출력 검증] 오류=['누락 제목'], 보고서=x\n[검증 미완료 - 초안 대체 답변]:\n"
TESTS = 5                                                   # 테스트 5개: t1~t5
ORIGINAL = "def keep():\n    return 0  # \n"


def _fixed(count):
    """앞에서부터 count개 결함을 고친 소스(fix1 … fixN 표시)."""
    marks = " ".join(f"fix{i}" for i in range(1, count + 1))
    return f"def keep():\n    return 0  # {marks}\n"


@pytest.fixture
def job(tmp_path, monkeypatch):
    """임시 저장소에 원본·테스트·request.json을 만든다."""
    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS", 10)
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_SELFFIX_STAGNATION_ROUNDS", 3)
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES", 1)
    source = tmp_path / "sample.py"
    source.write_text(ORIGINAL, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    job_id = "f" * 32
    request_path, _ = review._job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({
        "source_path": "sample.py", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "timeout_seconds": 3000, "output_limit": 1000, "error_path": None,
        "auto_apply": True, "test_paths": ["tests/test_sample.py"]}), encoding="utf-8")
    return source, job_id


def fake_run(source, proposals, verified=None):
    """리뷰 CLI는 proposals를 차례로 낸다(verified[i]가 False면 형식 거부). pytest는 t_i가 fix_i 있을 때 통과."""
    calls = {"review": []}
    verified = verified or [True] * len(proposals)

    def run(command, **_kwargs):
        if "pytest" in command:
            text = source.read_text(encoding="utf-8")
            oks = [f"fix{i}" in text for i in range(1, TESTS + 1)]
            body = "".join(f'<testcase classname="t" name="t{i}">' + ("" if ok else '<failure message="미해결"/>')
                           + "</testcase>" for i, ok in enumerate(oks, 1))
            xml = next(a for a in command if a.startswith("--junitxml=")).split("=", 1)[1]
            review.Path(xml).write_text(f"<testsuite>{body}</testsuite>", encoding="utf-8")
            return SimpleNamespace(returncode=0 if all(oks) else 1, stdout=b"pytest", stderr=b"")
        number = len(calls["review"])
        calls["review"].append(command)
        out_dir = review.Path(command[command.index("--output-dir") + 1])
        if verified[number]:
            (out_dir / "proposed.py").write_text(proposals[number], encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout=(VERIFIED if verified[number] else REJECTED).encode(), stderr=b"")

    run.calls = calls
    return run


def _run(job, monkeypatch, proposals, verified=None):
    source, job_id = job
    run = fake_run(source, proposals, verified)
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)
    review._run_review_job(job_id)
    return run, json.loads(review._job_files(job_id)[1].read_text(encoding="utf-8"))


def test_reproduce_keeps_going_while_improving_until_all_pass(job, monkeypatch):
    """재현: 매 라운드 1개씩 나아지면 3라운드에서 멈추지 않고 5라운드에서 전부 통과할 때까지 반복한다."""
    run, data = _run(job, monkeypatch, [_fixed(i) for i in range(1, 6)])
    source, _ = job
    assert len(run.calls["review"]) == 5
    assert source.read_text(encoding="utf-8") == _fixed(5)
    assert data["auto_apply_rounds"][-1]["situation"] == "all_passed"
    assert "stop_reason" not in data["auto_apply_rounds"][-1]          # 성공 종료는 '멈춤'이 아니다


def test_stagnation_stops_with_reason(job, monkeypatch):
    """제자리걸음: 3라운드 연속 통과 수가 늘지 않으면 안전 상한(10) 전에 멈추고 이유를 남긴다."""
    run, data = _run(job, monkeypatch, [ORIGINAL.replace("0", "1")] * 10)
    assert len(run.calls["review"]) == 3
    assert "제자리걸음" in data["auto_apply_rounds"][-1]["stop_reason"]


def test_format_rejected_after_retries_goes_to_next_round(job, monkeypatch):
    """형식 거부가 같은 라운드 재시도 한도를 넘어도 멈추지 않고 다음 라운드로 간다(대응표 next_round)."""
    proposals = [_fixed(1), "", "", _fixed(5)]
    run, data = _run(job, monkeypatch, proposals, [True, False, False, True])
    source, _ = job
    assert len(run.calls["review"]) == 4
    assert source.read_text(encoding="utf-8") == _fixed(5)
    situations = [r.get("situation") for r in data["auto_apply_rounds"]]
    assert situations == ["improved", "format_rejected", "format_rejected", "all_passed"]


def test_table_stop_action_is_followed(job, monkeypatch):
    """대응표에서 no_gain을 stop으로 바꾸면 그대로 따른다(코드가 아니라 표가 행동을 정한다)."""
    table = dict(review.project_config.MULTI_PERSONA_SELFFIX_ACTIONS, no_gain="stop")
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_SELFFIX_ACTIONS", table)
    run, data = _run(job, monkeypatch, [ORIGINAL.replace("0", "1")] * 3)
    assert len(run.calls["review"]) == 1
    assert "대응표" in data["auto_apply_rounds"][-1]["stop_reason"]


@pytest.mark.parametrize("change", [
    {"all_passed": "next_round"},       # 성공인데 계속 = 허용 안 함
    {"provider_fatal": "next_round"},   # 다시 불러도 같은 오류 = 허용 안 함
    {"no_gain": "jump"},                # 없는 행동
    None,                               # 표가 dict가 아님
])
def test_bad_action_table_is_rejected_before_ai(job, monkeypatch, change):
    """잘못된 입력: 대응표가 잘못되면 2라운드 AI를 부르기 전에 ValueError로 멈추고 그 이유를 남긴다."""
    table = None if change is None else dict(review.project_config.MULTI_PERSONA_SELFFIX_ACTIONS, **change)
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_SELFFIX_ACTIONS", table)
    run, data = _run(job, monkeypatch, [_fixed(1)] * 3)
    assert len(run.calls["review"]) == 1
    assert "ValueError" in data["auto_apply_rounds"][0]["error"]


@pytest.mark.parametrize("bad", [0, -1, True, "3"])
def test_bad_stagnation_limit_is_rejected(job, monkeypatch, bad):
    """잘못된 입력: 제자리걸음 기준이 1 미만·bool·문자열이면 AI를 더 부르지 않고 ValueError."""
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_SELFFIX_STAGNATION_ROUNDS", bad)
    run, data = _run(job, monkeypatch, [_fixed(1)] * 3)
    assert len(run.calls["review"]) == 1
    assert "ValueError" in data["auto_apply_rounds"][0]["error"]
