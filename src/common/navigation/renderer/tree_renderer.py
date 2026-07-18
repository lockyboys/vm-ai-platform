from __future__ import annotations

from src.common.formatter.tree_formatter import (
    TreeFormatter,
    TreeNode,
    TreeNodeType,
)

from src.common.navigation.navigation_model import NavigationModel
from src.common.navigation.navigation_node import NavigationNode

from .base_renderer import BaseRenderer


class TreeRenderer(BaseRenderer):
    """NavigationModel을 Tree 문자열로 출력한다."""

    def render(
        self,
        model: NavigationModel,
    ) -> str:
        return TreeFormatter.render_node(
            self._convert(model.root)
        )

    def _convert(
        self,
        node: NavigationNode,
    ) -> TreeNode:

        tree_node = TreeNode(
            name=node.label,
            node_type=TreeNodeType.DIRECTORY
            if node.children
            else TreeNodeType.LOGICAL,
        )

        for child in node.children:
            tree_node.add_child(
                self._convert(child)
            )

        return tree_node
