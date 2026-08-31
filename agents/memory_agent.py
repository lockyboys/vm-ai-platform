"""Subject-isolated persistent memory for the legacy AGI pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from config import LOG_PATH
from common.common_function import logger

_MAX_MEMORY_ENTRIES = int(os.getenv("SPS_MEMORY_MAX_ENTRIES", "1000"))


class MemoryAgent:
    """Store and search only the memories that belong to one authenticated subject."""

    def __init__(self, subject_id: str) -> None:
        normalized_subject = str(subject_id).strip()
        if not normalized_subject:
            raise ValueError("subject_id is required for memory access")
        self._directory = Path(LOG_PATH).resolve() / "agent_memory"
        self._directory.mkdir(parents=True, exist_ok=True)
        self._directory.chmod(0o700)
        subject_digest = hashlib.sha256(normalized_subject.encode("utf-8")).hexdigest()
        self.path = self._directory / f"{subject_digest}.json"
        self.memories = self._load()
        logger.info("💾 subject-isolated memory agent started (entries=%s)", len(self.memories))

    def store(self, task: str, result: dict[str, Any]) -> None:
        """Persist a bounded summary in the current subject's memory only."""
        entry = {
            "task": str(task),
            "summary": str(result)[:300],
            "keywords": self._extract_keywords(str(task)),
        }
        self.memories.append(entry)
        if len(self.memories) > _MAX_MEMORY_ENTRIES:
            self.memories = self.memories[-_MAX_MEMORY_ENTRIES:]
        self._save()

    def recall(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Return keyword-matched memories for the current subject only."""
        query_words = set(self._extract_keywords(str(query)))
        scored = [
            (len(query_words & set(memory.get("keywords", []))), memory)
            for memory in self.memories
        ]
        scored = [(score, memory) for score, memory in scored if score > 0]
        scored.sort(key=lambda item: -item[0])
        return [memory for _, memory in scored[:top_k]]

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        return list({word for word in text.lower().split() if len(word) > 2})

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                loaded = json.load(stream)
            return loaded if isinstance(loaded, list) else []
        except (OSError, json.JSONDecodeError):
            logger.warning("memory file could not be read; starting with an empty subject memory")
            return []

    def _save(self) -> None:
        descriptor, temporary_path = tempfile.mkstemp(
            dir=self._directory,
            prefix=".memory-",
            suffix=".tmp",
            text=True,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(self.memories, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, self.path)
        except OSError:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise
