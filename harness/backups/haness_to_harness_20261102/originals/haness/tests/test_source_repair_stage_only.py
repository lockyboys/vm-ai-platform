"""haness/source_repair.py 'git add까지만' 테스트 (2026-10-25 LuckyBoys: 자동 커밋 → add까지만, 수리 엔진 통일).

재현(수정 전): repair_source 적용 성공 시 _auto_commit이 git commit을 실행해 HEAD가 바뀌었다.
기대(수정 후): 적용 성공 시 git add만 하고 HEAD는 그대로, 대상 파일은 staged 상태여야 한다.
실제 임시 git 저장소에서 repair_source를 끝까지 실행해 확인한다(외부 네트워크·LLM 없음).
"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """임시 git 저장소 + 허용 목록에 올린 대상 파일 1개(커밋된 상태)."""
    spec = importlib.util.spec_from_file_location("source_repair_stage_t", ROOT / "haness/source_repair.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    git = lambda *a: subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    target = tmp_path / "pkg/calc.py"
    target.parent.mkdir()
    target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "init")
    monkeypatch.setattr(module, "_root", lambda: tmp_path)
    monkeypatch.setattr(module.config, "SPS_SOURCE_REPAIR_ALLOWED_PATHS", ("pkg/calc.py",))
    monkeypatch.setattr(module.config, "SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS", 30)
    monkeypatch.setattr(module.config, "SPS_SOURCE_REPAIR_AUDIT_DIR", "audit")
    return module, tmp_path, git


TEST = '''import importlib.util, unittest
spec = importlib.util.spec_from_file_location("calc", SOURCE_PATH)
calc = importlib.util.module_from_spec(spec); spec.loader.exec_module(calc)
class T(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calc.add(2, 3), 5)
'''


def _head(git) -> str:
    return git("rev-parse", "HEAD").stdout.decode().strip()


def test_applied_repair_is_staged_not_committed(repo):
    module, root, git = repo
    sha = module.read_repair_source("pkg/calc.py")["sha256"]
    before = _head(git)
    report = module.repair_source("pkg/calc.py", "return a - b", "return a + b", TEST, sha, dry_run=False)
    assert report["applied"] is True and report["git_stage"]["staged"] is True
    assert "git_commit" not in report
    assert _head(git) == before                                   # 커밋하지 않았다
    staged = git("diff", "--cached", "--name-only").stdout.decode().split()
    assert staged == ["pkg/calc.py"]                              # add까지만 했다
    assert "a + b" in (root / "pkg/calc.py").read_text(encoding="utf-8")


def test_dry_run_neither_writes_nor_stages(repo):
    module, root, git = repo
    sha = module.read_repair_source("pkg/calc.py")["sha256"]
    report = module.repair_source("pkg/calc.py", "return a - b", "return a + b", TEST, sha, dry_run=True)
    assert report["success"] is True and report["applied"] is False, report
    assert git("diff", "--cached", "--name-only").stdout.decode().strip() == ""
    assert "a - b" in (root / "pkg/calc.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("path", ["../x.py", "/etc/passwd", "pkg/other.py", ""])
def test_not_allowed_path_rejected(repo, path):
    module, _, _ = repo
    with pytest.raises(ValueError):
        module.read_repair_source(path)


def test_stage_only_reports_failure_without_raising(repo, monkeypatch):
    module, root, _ = repo

    class Fail:
        returncode, stdout, stderr = 1, b"", b""

    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: Fail())
    assert module._stage_only(root / "pkg/calc.py") == {"staged": False, "error": "git add 실패"}


def test_module_never_runs_git_commit():
    source = (ROOT / "haness/source_repair.py").read_text(encoding="utf-8")
    assert '"git", "commit"' not in source and "def _auto_commit" not in source
