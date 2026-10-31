"""run_pytest_verification 경로 검증 테스트(2026-10-25 LuckyBoys: haness/tests도 받도록).

재현: 수정 전에는 haness/tests/... 경로가 "Only tests/ paths are allowed."로 거부됐다.
규칙: tests/ 또는 haness/tests/ 아래만 허용. 그 밖·점 세그먼트·절대경로·비슷한 이름(haness/testsX)은 거부.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from harness.mcp.tools import pytest_tools


@pytest.fixture()
def root(monkeypatch, tmp_path: Path) -> Path:
    """임시 프로젝트 루트에 허용/비허용 위치의 테스트 파일을 만든다."""
    for relative in ["tests/test_a.py", "haness/tests/test_b.py", "haness/testsX/test_c.py", "haness/mcp/x.py"]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    monkeypatch.setattr(pytest_tools, "PROJECT_ROOT", tmp_path)
    return tmp_path


def test_haness_tests_path_is_accepted(root):
    # 재현 테스트: 수정 전에는 ValueError("Only tests/ ...")
    assert pytest_tools._validate_test_paths(["haness/tests/test_b.py", "tests/test_a.py"]) == [
        "haness/tests/test_b.py", "tests/test_a.py"]


@pytest.mark.parametrize("bad", ["haness/testsX/test_c.py", "haness/mcp/x.py", "haness/tests/../mcp/x.py",
                                 "haness", "/tmp/haness/tests/test_b.py", ""])
def test_other_paths_are_rejected(root, bad):
    with pytest.raises(ValueError):
        pytest_tools._validate_test_paths([bad])
