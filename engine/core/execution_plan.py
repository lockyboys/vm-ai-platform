from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExecutionPlan:

    name: str

    steps: list[str] = field(default_factory=list)
