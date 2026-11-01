"""블라인드 리뷰 '이어서 실행'(resume_job_id) 검증 (2026-11-01, LuckyBoys 선택 ①).

배경: 노트북 Ollama가 잠깐 꺼져 job a6f4e016…이 37/82에서 blocked_after_3_consecutive_failures로 멈췄다.
      submit()은 항상 새 job_id(새 결과 폴더)를 만들어 성공한 37건을 재사용하지 못했다.
규칙:
  - resume_job_id를 주면 그 job 폴더를 그대로 쓰고, 워커에 같은 job_id를 넘긴다(워커가 성공 결과를 건너뜀).
  - 이전 request/result/stderr/return_code는 지우지 않고 *.attemptN.* 로 보존한다(원본 보존).
  - 잘못된 job_id, 없는 job, 다른 provider, 아직 실행 중인 job은 프로세스를 띄우기 전에 거부한다.
실제 프로세스는 띄우지 않는다(subprocess.Popen 대역).
"""
import json

import pytest

from haness.mcp.tools import blind_review_jobs_v2 as jobs

OLD = "a6f4e01600d6446e8d265badbda3c522"


class _FakeStdin:
    def __init__(self, sink):
        self.sink = sink

    def write(self, data):
        self.sink.append(data)

    def close(self):
        pass


@pytest.fixture
def env(tmp_path, monkeypatch):
    """JOB_ROOT를 임시 폴더로 바꾸고 Popen을 대역으로 바꾼다. 띄운 명령과 stdin을 기록한다."""
    monkeypatch.setattr(jobs, "JOB_ROOT", tmp_path)
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            self.pid = 424242
            self.sent = []
            self.stdin = _FakeStdin(self.sent)
            calls.append(self)

    monkeypatch.setattr(jobs.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(jobs, "_alive", lambda pid: False)  # 기본: 이전 프로세스는 끝난 상태
    return tmp_path, calls


def _old_job(root, provider="ollama"):
    """멈춘 이전 job 폴더를 흉내 낸다."""
    d = root / OLD
    d.mkdir()
    (d / "request.json").write_text(json.dumps({"job_id": OLD, "provider": provider, "pid": 111}), encoding="utf-8")
    (d / "result.json").write_text('{"status": "blocked_after_3_consecutive_failures"}\n', encoding="utf-8")
    (d / "stderr.log").write_text("old stderr", encoding="utf-8")
    (d / "return_code").write_text("0", encoding="utf-8")
    return d


def _sent_payload(call):
    return json.loads(b"".join(call.sent).decode())


# ───────────── 정상 동작 ─────────────

def test_resume_reuses_same_job_id_and_folder(env):
    root, calls = env
    _old_job(root)
    req = jobs.submit("ollama", resume_job_id=OLD)
    assert req["job_id"] == OLD
    assert _sent_payload(calls[0]) == {"provider": "ollama", "job_id": OLD}  # 워커가 같은 결과 폴더를 쓴다
    assert json.loads((root / OLD / "request.json").read_text())["pid"] == 424242
    assert req["resumed_from_attempt"] == 1


def test_resume_preserves_previous_artifacts(env):
    root, _ = env
    d = _old_job(root)
    jobs.submit("ollama", resume_job_id=OLD)
    assert json.loads((d / "request.attempt1.json").read_text())["pid"] == 111
    assert "blocked_after_3" in (d / "result.attempt1.json").read_text()
    assert (d / "stderr.attempt1.log").read_text() == "old stderr"
    assert (d / "return_code.attempt1").read_text() == "0"
    assert not (d / "return_code").exists()  # 새 실행의 종료코드와 섞이지 않게 비운다


def test_second_resume_uses_next_attempt_number(env):
    root, _ = env
    d = _old_job(root)
    jobs.submit("ollama", resume_job_id=OLD)
    req = jobs.submit("ollama", resume_job_id=OLD)
    assert req["resumed_from_attempt"] == 2
    assert (d / "request.attempt2.json").exists()


def test_without_resume_creates_new_job(env):
    root, calls = env
    req = jobs.submit("ollama")
    assert req["job_id"] != OLD and len(req["job_id"]) == 32
    assert _sent_payload(calls[0])["job_id"] == req["job_id"]
    assert "resumed_from_attempt" not in req


# ───────────── 잘못된 입력 ─────────────

@pytest.mark.parametrize("bad", ["xyz", "A" * 32, "../" + OLD[:29], OLD + "0"])
def test_invalid_resume_job_id_rejected(env, bad):
    _, calls = env
    with pytest.raises(ValueError):
        jobs.submit("ollama", resume_job_id=bad)
    assert calls == []


def test_unknown_job_rejected(env):
    _, calls = env
    with pytest.raises(ValueError, match="not found"):
        jobs.submit("ollama", resume_job_id=OLD)
    assert calls == []


def test_provider_mismatch_rejected(env):
    root, calls = env
    _old_job(root, provider="gemini")
    with pytest.raises(ValueError, match="provider"):
        jobs.submit("ollama", resume_job_id=OLD)
    assert calls == []


def test_running_job_cannot_be_resumed(env, monkeypatch):
    root, calls = env
    d = _old_job(root)
    monkeypatch.setattr(jobs, "_alive", lambda pid: True)
    with pytest.raises(ValueError, match="running"):
        jobs.submit("ollama", resume_job_id=OLD)
    assert calls == [] and not (d / "request.attempt1.json").exists()  # 아무것도 옮기지 않는다


def test_invalid_provider_still_rejected(env):
    with pytest.raises(ValueError):
        jobs.submit("openai")
