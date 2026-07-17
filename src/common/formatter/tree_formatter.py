from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath


class TreeNodeType(str, Enum):
    """
    Tree Node의 의미 유형.

    DIRECTORY:
        디렉터리 또는 계층 그룹.

    FILE:
        실제 파일 Node.

    LOGICAL:
        테스트 케이스, 상태 등 논리적 Node.
    """

    DIRECTORY = "DIRECTORY"
    FILE = "FILE"
    LOGICAL = "LOGICAL"


@dataclass
class TreeNode:
    """
    파일 경로와 논리 계층을 함께 표현하는 Tree Node.
    """

    name: str
    node_type: TreeNodeType = TreeNodeType.LOGICAL
    children: dict[str, "TreeNode"] = field(
        default_factory=dict
    )

    @property
    def display_name(self) -> str:
        """
        Node 유형에 맞는 Console 표시명을 반환한다.
        """

        if self.node_type == TreeNodeType.DIRECTORY:
            if self.name == ".":
                return self.name

            return f"{self.name}/"

        return self.name

    def add_child(
        self,
        child: "TreeNode",
    ) -> "TreeNode":
        """
        Child Node를 등록하고 등록된 Node를 반환한다.
        """

        self.children[child.name] = child

        return child

    def add_path(
        self,
        path_parts: tuple[str, ...],
    ) -> None:
        """
        기존 Path Tree 호환성을 유지하면서
        경로 구성요소를 재귀적으로 등록한다.
        """

        if not path_parts:
            return

        current_part = path_parts[0]
        is_last = len(path_parts) == 1

        expected_type = (
            TreeNodeType.FILE
            if is_last
            else TreeNodeType.DIRECTORY
        )

        child = self.children.get(
            current_part
        )

        if child is None:
            child = TreeNode(
                name=current_part,
                node_type=expected_type,
            )
            self.add_child(child)

        elif (
            not is_last
            and child.node_type
            != TreeNodeType.DIRECTORY
        ):
            child.node_type = TreeNodeType.DIRECTORY

        child.add_path(path_parts[1:])


class TreeFormatter:
    """
    파일 경로 목록을 표준 Tree 문자열로 변환한다.

    입력:
        [
            "src/common/formatter/pretty_output.py",
            "src/common/formatter/pretty_formatter.py",
            "tests/common/formatter/test_pretty_output.py",
        ]

    출력:
        .
        ├── src/
        │   └── common/
        │       └── formatter/
        │           ├── pretty_formatter.py
        │           └── pretty_output.py
        └── tests/
            └── common/
                └── formatter/
                    └── test_pretty_output.py
    """

    DIRECTORY_SUFFIX = "/"

    @classmethod
    def render(
        cls,
        paths: Iterable[str],
        root_name: str = ".",
    ) -> str:
        normalized_paths = cls.normalize_paths(paths)

        if not normalized_paths:
            return root_name

        root = TreeNode(
            name=root_name,
            node_type=TreeNodeType.DIRECTORY,
        )

        for normalized_path in normalized_paths:
            path_parts = tuple(
                part
                for part in PurePosixPath(
                    normalized_path
                ).parts
                if part not in {
                    "",
                    ".",
                    "/",
                }
            )

            root.add_path(path_parts)

        lines = [root_name]

        cls._render_children(
            node=root,
            prefix="",
            lines=lines,
        )

        return "\n".join(lines)

    @classmethod
    def render_node(
        cls,
        root: TreeNode,
    ) -> str:
        """
        이미 구성된 TreeNode 계층을
        표준 Tree 문자열로 변환한다.
        """

        lines = [
            root.display_name
        ]

        cls._render_children(
            node=root,
            prefix="",
            lines=lines,
        )

        return "\n".join(lines)

    @classmethod
    def normalize_paths(
        cls,
        paths: Iterable[str],
    ) -> list[str]:
        """
        경로 구분자를 POSIX 형식으로 통일하고
        빈 값과 중복 경로를 제거한다.
        """

        normalized_paths: set[str] = set()

        for path in paths:
            normalized_path = cls.normalize_path(
                path
            )

            if normalized_path:
                normalized_paths.add(
                    normalized_path
                )

        return sorted(
            normalized_paths,
            key=cls._sort_key,
        )

    @staticmethod
    def normalize_path(
        path: str,
    ) -> str:
        normalized_path = str(path).strip()

        if not normalized_path:
            return ""

        normalized_path = normalized_path.replace(
            "\\",
            "/",
        )

        while normalized_path.startswith("./"):
            normalized_path = normalized_path[2:]

        normalized_path = normalized_path.strip("/")

        return normalized_path

    @classmethod
    def _render_children(
        cls,
        node: TreeNode,
        prefix: str,
        lines: list[str],
    ) -> None:
        children = sorted(
            node.children.values(),
            key=cls._node_sort_key,
        )

        for index, child in enumerate(children):
            is_last = index == len(children) - 1

            connector = (
                "└── "
                if is_last
                else "├── "
            )

            child_prefix = (
                "    "
                if is_last
                else "│   "
            )

            display_name = child.display_name

            lines.append(
                f"{prefix}{connector}{display_name}"
            )

            cls._render_children(
                node=child,
                prefix=f"{prefix}{child_prefix}",
                lines=lines,
            )

    @staticmethod
    def _sort_key(
        path: str,
    ) -> tuple[str, ...]:
        return tuple(
            part.lower()
            for part in PurePosixPath(path).parts
        )

    @staticmethod
    def _node_sort_key(
        node: TreeNode,
    ) -> tuple[int, str]:
        """
        동일 계층에서는 디렉터리를 파일보다 먼저 표시한다.
        """

        node_type_order = {
            TreeNodeType.DIRECTORY: 0,
            TreeNodeType.FILE: 1,
            TreeNodeType.LOGICAL: 2,
        }.get(
            node.node_type,
            99,
        )

        return (
            node_type_order,
            node.name.lower(),
        )
    @classmethod
    def _build_path_tree(
        cls,
        paths: Iterable[str],
        *,
        root_name: str,
    ) -> TreeNode:
        root = TreeNode(
            name=root_name,
            node_type=TreeNodeType.DIRECTORY,
        )

        for raw_path in paths:
            normalized_path = raw_path.replace(
                "\\",
                "/",
            ).strip("/")

            if not normalized_path:
                continue

            parts = [
                part
                for part in normalized_path.split("/")
                if part
            ]

            current_node = root

            for index, part in enumerate(parts):
                is_last = index == len(parts) - 1

                node_type = (
                    TreeNodeType.FILE
                    if is_last
                    else TreeNodeType.DIRECTORY
                )

                child = cls._find_child(
                    current_node,
                    part,
                )

                if child is None:
                    child = TreeNode(
                        name=part,
                        node_type=node_type,
                    )
                    current_node.add_child(child)

                current_node = child

        return root

    @staticmethod
    def _find_child(
        parent: TreeNode,
        name: str,
    ) -> TreeNode | None:
        """
        Parent의 직접 Child 중 이름이 같은 Node를 반환한다.
        """

        return parent.children.get(name)

