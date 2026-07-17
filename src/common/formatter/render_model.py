from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
from .tree_formatter import TreeNode


@dataclass(frozen=True)
class TableModel:
    """테이블 출력 데이터."""

    columns: Sequence[str]
    rows: Sequence[Sequence[Any]]


@dataclass(frozen=True)
class TreeModel:
    title: str
    root: TreeNode | None = None
    paths: tuple[str, ...] = field(
        default_factory=tuple
    )
    root_name: str = "."


@dataclass(frozen=True)
class RenderModel:
    """Pretty Formatter 공통 출력 모델."""

    title: str
    icon: str = ""
    summary: Mapping[str, Any] = field(
        default_factory=dict
    )
    table: TableModel | None = None
    trees: Sequence[TreeModel] = field(
        default_factory=tuple
    )
    body: Sequence[str] = field(
        default_factory=tuple
    )
    status: str = "SUCCESS"
