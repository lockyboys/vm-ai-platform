from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionContext:
    """
    SPS Engine Execution Context

    모든 Engine는 Context 하나만 전달한다.
    """

    request: dict[str, Any]

    repository: dict[str, Any] = field(default_factory=dict)

    execution_plan: Any = None

    identifier: str | None = None

    transaction: Any = None

    result: Any = None

    shared: dict[str, Any] = field(default_factory=dict)
