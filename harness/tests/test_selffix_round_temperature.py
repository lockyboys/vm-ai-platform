"""라운드마다 작업 AI의 무작위성(temperature)을 낮추는 기능 테스트 (2026-11-14, LuckyBoys 결정).

결정: 1차 0.4 → 2차 0.2 → 3차 0.0 (config.MULTI_PERSONA_AUTO_APPLY_ROUND_TEMPERATURES, 최대 라운드 3).
이유: 같은 AI라도 매번 답이 달라 한 번 맞힌 것을 다음에 틀릴 수 있다. 재시도할수록 답을 고정해
      피드백(실패 테스트)에 맞춘 수정만 하도록 한다.
확인할 것
1) 라운드 번호 → 온도(설정보다 라운드가 많으면 마지막 값 유지)
2) 잘못된 설정(빈 값, 범위 밖, 숫자 아님)은 시작 전에 ValueError
3) 재시도 라운드 명령에 --agent-temperature 가 붙는다(2차 0.2, 3차 0.0), 전용 CLI(llm=None)는 붙이지 않는다.
4) CLI가 값을 받아 작업 AI 온도로 쓰고, 잘못된 값(문자, 범위 밖)은 거부한다. 인자가 없으면 예전 0.4.
LLM 호출 없음(subprocess.run 대역, CLI는 그래프만 만들고 실행하지 않음).
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import config as project_config
from harness.mcp.tools import multi_persona_tools as review

ROOT = Path(project_config.PROJECT_ROOT)
CLI = ROOT / "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py"


# ------------------------------------------------------------------ 1) 2) 라운드 → 온도
def test_round_temperatures_follow_config():
    """1차 0.4, 2차 0.2, 3차 0.0, 그 뒤는 마지막 값 유지."""
    assert [review._round_temperature(n) for n in (1, 2, 3, 4)] == [0.4, 0.2, 0.0, 0.0]


@pytest.mark.parametrize("bad", [(), (0.4, 1.5), (0.4, -0.1), ("0.2",), (True,), None])
def test_bad_temperature_config_rejected(monkeypatch, bad):
    """잘못된 설정은 AI를 부르기 전에 ValueError."""
    monkeypatch.setattr(project_config, "MULTI_PERSONA_AUTO_APPLY_ROUND_TEMPERATURES", bad)
    with pytest.raises(ValueError):
        review._round_temperature(2)


@pytest.mark.parametrize("bad_number", [0, -1, "2", 1.5])
def test_bad_round_number_rejected(bad_number):
    """잘못된 입력: 라운드 번호는 1 이상 정수."""
    with pytest.raises(ValueError):
        review._round_temperature(bad_number)


# ------------------------------------------------------------------ 3) 재시도 라운드 명령
ORIGINAL = "def keep():\n    return 1\n"
FIRST = "def keep():\n    return 2\n"
SECOND = "def keep():\n    return 4\n"
GOOD = "def keep():\n    return 3\n"
VERIFIED = "[출력 검증] 오류=[], 보고서=x\n[최종 검증된 답변]:\n본문\n"


@pytest.fixture
def job(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    source = tmp_path / "sample.py"
    source.write_text(ORIGINAL, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    job_id = "f" * 32
    request_path, _ = review._job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({
        "source_path": "sample.py", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "timeout_seconds": 600, "output_limit": 1000, "error_path": None, "provider": "gemini",
        "auto_apply": True, "test_paths": ["tests/test_sample.py"]}), encoding="utf-8")
    return source, job_id


def _fake_run(source, proposals):
    calls = []

    def run(command, **_kwargs):
        if "pytest" in command:
            ok = source.read_text(encoding="utf-8") == GOOD
            xml = next(arg for arg in command if arg.startswith("--junitxml=")).split("=", 1)[1]
            body = "" if ok else '<failure message="keep() 틀림"/>'
            review.Path(xml).write_text(f'<testsuite><testcase classname="t" name="test_ok">{body}</testcase></testsuite>',
                                        encoding="utf-8")
            return SimpleNamespace(returncode=0 if ok else 1, stdout=b"pytest", stderr=b"")
        out_dir = review.Path(command[command.index("--output-dir") + 1])
        (out_dir / "proposed.py").write_text(proposals[len(calls)], encoding="utf-8")
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=VERIFIED.encode(), stderr=b"")

    run.calls = calls
    return run


def _temp_arg(command):
    return command[command.index("--agent-temperature") + 1] if "--agent-temperature" in command else None


def test_retry_rounds_lower_temperature(job, monkeypatch):
    """1차(기존 명령)·2차·3차 순서로 0.4(인자 없음=CLI 기본)·0.2·0.0이 쓰이고, 기록에도 남는다."""
    source, job_id = job
    monkeypatch.setattr(project_config, "MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS", 3)
    run = _fake_run(source, [FIRST, SECOND, GOOD])
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)
    review._run_review_job(job_id)
    data = json.loads(review._job_files(job_id)[1].read_text(encoding="utf-8"))
    assert source.read_text(encoding="utf-8") == GOOD
    assert [_temp_arg(c) for c in run.calls] == [None, "0.2", "0.0"]
    assert [r.get("agent_temperature") for r in data["auto_apply_rounds"]] == [None, 0.2, 0.0]


def test_dedicated_cli_gets_no_temperature_arg(job, monkeypatch):
    """전용 CLI(llm=None, 이 인자를 모름)에는 --agent-temperature를 붙이지 않는다."""
    source, job_id = job
    request_path, _ = review._job_files(job_id)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request_path.write_text(json.dumps({**request, "provider": "ollama_gemma"}), encoding="utf-8")
    run = _fake_run(source, [FIRST, GOOD])
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)
    review._run_review_job(job_id)
    assert all(_temp_arg(c) is None for c in run.calls)


# ------------------------------------------------------------------ 4) CLI가 값을 받는지
_PROBE = (
    "import runpy, sys\n"
    "cli = sys.argv[1]\n"
    "sys.argv = [cli, *sys.argv[2:]]\n"
    "g = runpy.run_path(cli, run_name='probe')\n"  # __main__이 아니므로 리뷰는 실행되지 않음
    "print('PROBE=' + repr(g['AGENT_TEMPERATURE']))\n"
)


def _probe(*args):
    return subprocess.run([sys.executable, "-c", _PROBE, str(CLI), "--provider", "gemini", "--no-web-search", *args],
                          cwd=ROOT, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("value, expected", [(None, 0.4), ("0.2", 0.2), ("0.0", 0.0)])
def test_cli_reads_agent_temperature(value, expected):
    done = _probe(*(["--agent-temperature", value] if value else []))
    assert done.returncode == 0, done.stderr[-1500:]
    assert done.stdout.strip().splitlines()[-1] == f"PROBE={expected!r}"


@pytest.mark.parametrize("bad", ["abc", "1.5", "-0.1"])
def test_cli_rejects_bad_agent_temperature(bad):
    """잘못된 입력: 숫자가 아니거나 0.0~1.0 밖이면 CLI가 실행 전에 멈춘다."""
    assert _probe("--agent-temperature", bad).returncode != 0
