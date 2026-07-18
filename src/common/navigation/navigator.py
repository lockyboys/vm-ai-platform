from __future__ import annotations

from src.common.navigation.navigation_model import NavigationModel
from src.common.navigation.navigation_node import NavigationNode


class Navigator:
    """NavigationModel을 탐색하는 Navigator."""

    def __init__(
        self,
        model: NavigationModel,
    ) -> None:
        self._model = model
        self._current = model.root

    @property
    def current(self) -> NavigationNode:
        return self._current

    def goto(
        self,
        key: str,
    ) -> NavigationNode:
        node = self._model.require(key)
        self._current = node
        return node

    def reset(self) -> NavigationNode:
        self._current = self._model.root
        return self._current

    def children(self) -> list[NavigationNode]:
        return list(self._current.children)

    def path(self) -> list[str]:
        path: list[str] = []

        def visit(node: NavigationNode, stack: list[str]) -> bool:
            stack.append(node.key)

            if node is self._current:
                path.extend(stack)
                return True

            for child in node.children:
                if visit(child, stack.copy()):
                    return True

            return False

        visit(self._model.root, [])

        return path
