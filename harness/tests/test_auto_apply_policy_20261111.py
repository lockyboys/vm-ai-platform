"""auto_apply 적용 규칙(policy) 테스트 (2026-11-11, LuckyBoys 요청: "통과 식이 늘었으면 적용").

재현 배경: 어려운 시험에서 Gemini가 오류 100개 중 99개를 고쳤지만 1개 때문에 전부 되돌려졌다.
"improve" 규칙은 퇴행(기준선에서 통과하던 테스트가 새로 실패) 없이 통과 수가 늘면 적용해야 한다.
pytest 실행(subprocess.run)은 대역으로 바꿔 --junitxml 결과 파일만 만들어 준다(LLM·systemd 없음).
"""
import hashlib
from types import SimpleNamespace

import pytest

from harness.mcp.tools import auto_apply

ORIGINAL = "X = 1\n"
PROPOSED = "X = 2\n"
TESTS = ["tests/test_pkg.py"]


@pytest.fixture
def repo(tmp_path):
    """임시 저장소: 원본·제안·job 폴더·테스트 파일."""
    source = tmp_path / "pkg.py"
    source.write_text(ORIGINAL, encoding="utf-8")
    proposed = tmp_path / "proposed.py"
    proposed.write_text(PROPOSED, encoding="utf-8")
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_pkg.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    return tmp_path, source, proposed, job_dir, sha


def fake_pytest(monkeypatch, before, after, write_xml=True):
    """첫 호출(원본 기준선)은 before, 다음 호출(제안 적용 후)은 after 결과를 junit xml로 쓴다.

    before/after: {테스트 이름: 통과 여부}. 전부 통과면 returncode 0, 아니면 1.
    """
    results = iter([before, after])

    def run(cmd, **_kwargs):
        outcome = next(results)
        xml_arg = next(arg for arg in cmd if arg.startswith("--junitxml="))
        if write_xml:
            cases = "".join(
                f'<testcase classname="t" name="{name}">{"" if ok else "<failure/>"}</testcase>'
                for name, ok in outcome.items())
            with open(xml_arg.split("=", 1)[1], "w", encoding="utf-8") as handle:
                handle.write(f"<testsuites><testsuite>{cases}</testsuite></testsuites>")
        return SimpleNamespace(returncode=0 if all(outcome.values()) else 1, stdout=b"fake")

    monkeypatch.setattr(auto_apply.subprocess, "run", run)


def test_improve_applies_partial_fix(repo, monkeypatch):
    """재현: 1/3 → 2/3 통과, 퇴행 없음 → 적용(partial)."""
    root, source, proposed, job_dir, sha = repo
    fake_pytest(monkeypatch, {"a": True, "b": False, "c": False}, {"a": True, "b": True, "c": False})
    state = auto_apply.apply_with_rollback(source, proposed, job_dir, sha, TESTS, 600, root, policy="improve")
    assert state["applied"] is True and state["partial"] is True
    assert (state["tests_passed_before"], state["tests_passed_after"], state["tests_total"]) == (1, 2, 3)
    assert source.read_text(encoding="utf-8") == PROPOSED
    assert (job_dir / "original.py").read_text(encoding="utf-8") == ORIGINAL


def test_improve_rolls_back_on_regression(repo, monkeypatch):
    """통과 수는 늘었지만 기준선에서 통과하던 a가 새로 실패 → 되돌림."""
    root, source, proposed, job_dir, sha = repo
    fake_pytest(monkeypatch, {"a": True, "b": False, "c": False}, {"a": False, "b": True, "c": True})
    state = auto_apply.apply_with_rollback(source, proposed, job_dir, sha, TESTS, 600, root, policy="improve")
    assert state["rolled_back"] is True and "broke 1" in state["reason"]
    assert state["newly_failed"] == ["t::a"]
    assert source.read_text(encoding="utf-8") == ORIGINAL


def test_improve_rolls_back_without_gain(repo, monkeypatch):
    """통과 수가 그대로면 되돌림."""
    root, source, proposed, job_dir, sha = repo
    fake_pytest(monkeypatch, {"a": True, "b": False}, {"a": True, "b": False})
    state = auto_apply.apply_with_rollback(source, proposed, job_dir, sha, TESTS, 600, root, policy="improve")
    assert state["rolled_back"] is True and "did not increase" in state["reason"]
    assert source.read_text(encoding="utf-8") == ORIGINAL


def test_improve_full_pass_is_not_partial(repo, monkeypatch):
    """전부 통과하면 적용하되 partial은 False."""
    root, source, proposed, job_dir, sha = repo
    fake_pytest(monkeypatch, {"a": True, "b": False}, {"a": True, "b": True})
    state = auto_apply.apply_with_rollback(source, proposed, job_dir, sha, TESTS, 600, root, policy="improve")
    assert state["applied"] is True and state["partial"] is False


def test_all_pass_keeps_old_behavior(repo, monkeypatch):
    """all_pass 규칙: 통과 수가 늘어도 하나라도 실패하면 되돌림(기준선 실행 없음)."""
    root, source, proposed, job_dir, sha = repo
    fake_pytest(monkeypatch, {"a": True, "b": True, "c": False}, {})
    state = auto_apply.apply_with_rollback(source, proposed, job_dir, sha, TESTS, 600, root, policy="all_pass")
    assert state["rolled_back"] is True and state["reason"].endswith("tests failed after applying the proposal")
    assert source.read_text(encoding="utf-8") == ORIGINAL


def test_improve_rolls_back_when_results_missing(repo, monkeypatch):
    """테스트별 결과 파일이 없으면 판단 근거가 없으므로 되돌림."""
    root, source, proposed, job_dir, sha = repo
    fake_pytest(monkeypatch, {"a": False}, {"a": False}, write_xml=False)
    state = auto_apply.apply_with_rollback(source, proposed, job_dir, sha, TESTS, 600, root, policy="improve")
    assert state["rolled_back"] is True and "unavailable" in state["reason"]
    assert source.read_text(encoding="utf-8") == ORIGINAL


def test_improve_rolls_back_compile_error(repo, monkeypatch):
    """문법 오류 제안은 규칙과 관계없이 되돌림."""
    root, source, proposed, job_dir, sha = repo
    proposed.write_text("def broken(:\n", encoding="utf-8")
    fake_pytest(monkeypatch, {"a": False}, {"a": True})
    state = auto_apply.apply_with_rollback(source, proposed, job_dir, sha, TESTS, 600, root, policy="improve")
    assert state["rolled_back"] is True and state["reason"].startswith("SyntaxError")
    assert source.read_text(encoding="utf-8") == ORIGINAL


@pytest.mark.parametrize("bad", ["partial", "", "ALL_PASS", 1])
def test_invalid_policy_rejected(repo, bad):
    """잘못된 입력: 허용 목록 밖 규칙 이름은 원본을 건드리기 전에 ValueError."""
    root, source, proposed, job_dir, sha = repo
    with pytest.raises(ValueError):
        auto_apply.apply_with_rollback(source, proposed, job_dir, sha, TESTS, 600, root, policy=bad)
    assert source.read_text(encoding="utf-8") == ORIGINAL


def test_default_policy_comes_from_config(monkeypatch):
    """policy=None이면 루트 config 값을 쓴다."""
    monkeypatch.setattr(auto_apply.project_config, "MULTI_PERSONA_AUTO_APPLY_POLICY", "improve", raising=False)
    assert auto_apply.resolve_policy(None) == "improve"
