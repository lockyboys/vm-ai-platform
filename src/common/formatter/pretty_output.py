from __future__ import annotations

from typing import (
    Any,
    Iterable,
    Mapping,
    Sequence,
)

from .formatter_config import FormatterConfig
from .pretty_formatter import PrettyFormatter
from .render_model import (
    RenderModel,
    TableModel,
    TreeModel,
)
from .tree_formatter import TreeFormatter


class PrettyOutput:
    """
    SPS 공통 출력 형식을 생성하는 간편 출력 클래스.

    Tool 개발자는 RenderModel을 직접 생성하지 않고
    title, summary, body, table, tree만 전달한다.
    """

    DEFAULT_ICON_MAPPING: dict[str, str] = {
        "Source Search": "📄",
        "Source Read": "📖",
        "Table Schema": "🗂",
        "Table Data": "📊",
        "Git Status": "🌿",
        "Git Diff": "🔀",
        "Repository Search": "🔍",
        "Repository Read": "📚",
        "Success": "✅",
        "Warning": "⚠️",
        "Error": "❌",
        "Info": "ℹ️",
    }

    def __init__(
        self,
        title: str,
        *,
        icon: str | None = None,
        status: str = "SUCCESS",
        config: FormatterConfig | None = None,
    ) -> None:
        if not title or not title.strip():
            raise ValueError(
                "PrettyOutput title must not be empty."
            )

        self.title = title.strip()

        self.icon = (
            icon
            if icon is not None
            else self.DEFAULT_ICON_MAPPING.get(
                self.title,
                "📌",
            )
        )

        self.status = status.upper()
        self.formatter = PrettyFormatter(
            config
        )

        self._summary: dict[str, Any] = {}
        self._body: list[str] = []
        self._table: TableModel | None = None
        self._trees: list[TreeModel] = []

    def summary(
        self,
        values: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> PrettyOutput:
        """
        Summary 값을 추가한다.

        Examples:
            output.summary(
                {"Branch": "main"}
            )

            output.summary(
                Branch="main",
                Modified=3,
            )
        """

        if values:
            self._summary.update(values)

        if kwargs:
            self._summary.update(kwargs)

        return self

    def body(
        self,
        *lines: Any,
    ) -> PrettyOutput:
        """
        Body 문장을 추가한다.
        """

        self._body.extend(
            str(line)
            for line in lines
        )

        return self

    def table(
        self,
        columns: Sequence[str],
        rows: Sequence[Sequence[Any]],
    ) -> PrettyOutput:
        """
        Table 데이터를 설정한다.
        """

        self._table = TableModel(
            columns=columns,
            rows=rows,
        )

        return self

    def tree(
        self,
        title: str,
        paths: Iterable[str],
        *,
        root_name: str = ".",
    ) -> PrettyOutput:
        """
        파일 및 디렉터리 경로를
        표준 Tree Section으로 추가한다.

        Examples:
            output.tree(
                title="Modified",
                paths=[
                    ".gitignore",
                    "src/common/file.py",
                ],
            )
        """

        normalized_title = title.strip()

        if not normalized_title:
            raise ValueError(
                "Tree title must not be empty."
            )

        self._trees.append(
            TreeModel(
                title=normalized_title,
                paths=tuple(paths),
                root_name=root_name,
            )
        )

        return self

    def success(self) -> PrettyOutput:
        self.status = "SUCCESS"
        return self

    def warning(self) -> PrettyOutput:
        self.status = "WARNING"
        return self

    def error(self) -> PrettyOutput:
        self.status = "ERROR"
        return self

    def info(self) -> PrettyOutput:
        self.status = "INFO"
        return self

    def render(self) -> str:
        """
        현재 설정을 SPS 공통 출력 문자열로 변환한다.
        """

        model = RenderModel(
            title=self.title,
            icon=self.icon,
            summary=self._summary,
            body=tuple(self._body),
            table=self._table,
            trees=tuple(self._trees),
            status=self.status,
        )

        return self.formatter.render(
            model
        )

    def print(self) -> None:
        """
        현재 출력을 Console에 출력한다.
        """

        print(
            self.render()
        )

    def __str__(self) -> str:
        return self.render()
        
    def logical_tree(
        self,
        title: str,
        root: TreeNode,
    ) -> "PrettyOutput":
        if not title.strip():
            raise ValueError(
                "Tree title must not be empty."
            )

        self._trees.append(
            TreeModel(
                title=title,
                root=root,
            )
        )

        return self