"""Regression tests for source-tool secret and runtime boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.mcp.tools import source_tools


def test_source_search_excludes_runtime_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "visible.py").write_text("needle = 'visible'\n", encoding="utf-8")
    runtime_path = tmp_path / "runtime"
    runtime_path.mkdir()
    (runtime_path / "oauth_clients.json").write_text(
        "needle = 'secret'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(source_tools, "PROJECT_ROOT", tmp_path)

    results = source_tools.source_search("needle")

    assert [result["path"] for result in results] == ["visible.py"]


@pytest.mark.parametrize(
    "path",
    [
        "runtime/oauth_clients.json",
        ".runtime/cache.json",
        ".npm-cache/cache.json",
    ],
)
def test_source_read_denies_runtime_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    path: str,
) -> None:
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    target.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(source_tools, "PROJECT_ROOT", tmp_path)

    with pytest.raises(PermissionError):
        source_tools.source_read(path)


def test_source_read_allows_engine_runtime_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "engine" / "runtime" / "file_runtime_adapter.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("adapter_name = 'file_runtime'\n", encoding="utf-8")
    monkeypatch.setattr(source_tools, "PROJECT_ROOT", tmp_path)

    result = source_tools.source_read("engine/runtime/file_runtime_adapter.py")

    assert result["content"] == [
        {"line_no": 1, "line_text": "adapter_name = 'file_runtime'"}
    ]
