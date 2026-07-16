from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExecutionResult:

    success: bool = True

    identifier: str | None = None

    message: str = ""

    warnings: list[str] = field(default_factory=list)

    artifacts: list[str] = field(default_factory=list)
