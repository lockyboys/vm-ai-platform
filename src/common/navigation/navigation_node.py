from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator


class NavigationNodeType(str, Enum):
    """Navigation Node의 의미 유형."""

    ROOT = "ROOT"
    GROUP = "GROUP"
    ITEM = "ITEM"
    VALUE = "VALUE"


@dataclass
class NavigationNode:
    """Repository와 Tool 결과를 표현하는 범용 탐색 Node."""

    key: str
    label: str
    node_type: NavigationNodeType = NavigationNodeType.ITEM
    value: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list["NavigationNode"] = field(default_factory=list)

    def add_child(
        self,
        child: "NavigationNode",
    ) -> "NavigationNode":
        """Child Node를 추가하고 추가된 Node를 반환한다."""

        if not isinstance(child, NavigationNode):
            raise TypeError(
                "child must be an instance of NavigationNode"
            )

        if self.find_child(child.key) is not None:
            raise ValueError(
                f"duplicate child key: {child.key}"
            )

        self.children.append(child)

        return child

    def find_child(
        self,
        key: str,
    ) -> "NavigationNode | None":
        """현재 Node의 직접 Child에서 key가 같은 Node를 찾는다."""

        for child in self.children:
            if child.key == key:
                return child

        return None

    def walk(self) -> Iterator["NavigationNode"]:
        """현재 Node부터 모든 하위 Node를 깊이 우선으로 순회한다."""

        yield self

        for child in self.children:
            yield from child.walk()

    @property
    def is_leaf(self) -> bool:
        """하위 Node가 없는지 반환한다."""

        return not self.children
