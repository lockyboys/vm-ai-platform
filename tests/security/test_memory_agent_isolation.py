"""Regression tests for subject-isolated legacy AGI memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents import memory_agent


def test_memory_is_isolated_and_persisted_atomically(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(memory_agent, "LOG_PATH", str(tmp_path))

    first = memory_agent.MemoryAgent("member-one")
    first.store("private health analysis", {"score": 91})

    second = memory_agent.MemoryAgent("member-two")
    second.store("budget analytics", {"score": 72})
    assert second.recall("private health analysis") == []

    reloaded_first = memory_agent.MemoryAgent("member-one")
    recalled = reloaded_first.recall("private health analysis")
    assert len(recalled) == 1
    assert recalled[0]["summary"] == "{'score': 91}"

    memory_files = list((tmp_path / "agent_memory").glob("*.json"))
    assert len(memory_files) == 2
    assert all("member-" not in path.name for path in memory_files)
    assert all(path.stat().st_mode & 0o077 == 0 for path in memory_files)


def test_memory_requires_a_subject(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(memory_agent, "LOG_PATH", str(tmp_path))

    with pytest.raises(ValueError, match="subject_id"):
        memory_agent.MemoryAgent("")
