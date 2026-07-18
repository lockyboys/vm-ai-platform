from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from src.common.navigation.navigation_node import NavigationNode


@dataclass
class NavigationModel:
    """Navigation Node 계층과 탐색 기능을 관리한다."""

    root: NavigationNode

    def walk(self) -> Iterator[NavigationNode]:
        """Root부터 전체 Navigation Node를 순회한다."""

        yield from self.root.walk()

    def find(
        self,
        key: str,
    ) -> NavigationNode | None:
        """전체 Navigation Tree에서 key가 같은 첫 번째 Node를 찾는다."""

        for node in self.walk():
            if node.key == key:
                return node

        return None

    def require(
        self,
        key: str,
    ) -> NavigationNode:
        """Node를 조회하고 존재하지 않으면 KeyError를 발생시킨다."""

        node = self.find(key)

        if node is None:
            raise KeyError(
                f"navigation node not found: {key}"
            )

        return node

    def add(
        self,
        parent_key: str,
        child: NavigationNode,
    ) -> NavigationNode:
        """Parent Node를 찾아 Child Node를 추가한다."""

        parent = self.require(parent_key)

        return parent.add_child(child)

    def contains(
        self,
        key: str,
    ) -> bool:
        """지정한 key의 Node 존재 여부를 반환한다."""

        return self.find(key) is not None

    def count(self) -> int:
        """전체 Navigation Node 수를 반환한다."""

        return sum(
            1
            for _ in self.walk()
        )
