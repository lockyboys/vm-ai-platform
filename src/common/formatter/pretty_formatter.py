from datetime import datetime
from typing import Any, Iterable, Sequence

from .formatter_config import FormatterConfig
from .tree_formatter import TreeFormatter
from .render_model import (
    RenderModel,
    TableModel,
    TreeModel,
)


class PrettyFormatter:
    """Story Programming Framework 공통 Console Formatter."""

    def __init__(
        self,
        config: FormatterConfig | None = None,
    ) -> None:
        self.config = config or FormatterConfig()

    def render(
        self,
        model: RenderModel,
    ) -> str:
        """RenderModel 전체를 문자열로 변환한다."""

        sections: list[str] = [
            self.render_header(
                model.title,
                model.icon,
            ),
        ]

        if model.summary:
            sections.append(
                self.render_summary(
                    model.summary
                )
            )

        if model.body:
            sections.append(
                self.render_body(
                    model.body
                )
            )

        if model.table is not None:
            sections.append(
                self.render_table(
                    model.table
                )
            )

        for tree in model.trees:
            sections.append(
                self.render_tree(
                    tree
                )
            )

        sections.append(
            self.render_footer(
                model.status
            )
        )

        return "\n\n".join(
            section
            for section in sections
            if section
        )

    def render_header(
        self,
        title: str,
        icon: str = "",
    ) -> str:
        """공통 Header를 생성한다."""

        display_title = (
            f"{icon} {title}".strip()
        )

        line = (
            self.config.header_character
            * self.config.width
        )

        return "\n".join(
            [
                line,
                display_title.center(
                    self.config.width
                ),
                line,
            ]
        )

    def render_summary(
        self,
        summary: dict[str, Any] | Any,
    ) -> str:
        """Key-Value 기반 Summary를 생성한다."""

        rows = []

        for key, value in summary.items():
            display_value = (
                self._normalize_value(
                    value
                )
            )

            rows.append(
                f"{str(key):<20}"
                f"{self.config.key_value_separator}"
                f"{display_value}"
            )

        return "\n".join(
            [
                "Summary",
                self.render_divider(),
                *rows,
            ]
        )

    def render_body(
        self,
        body: Iterable[str],
    ) -> str:
        """일반 본문을 출력한다."""

        return "\n".join(
            [
                "Body",
                self.render_divider(),
                *(
                    str(line)
                    for line in body
                ),
            ]
        )

    def render_table(
        self,
        table: TableModel,
    ) -> str:
        """고정 폭 계산 기반 Console Table을 생성한다."""

        columns = [
            str(column)
            for column in table.columns
        ]

        normalized_rows = [
            [
                self._normalize_value(
                    value
                )
                for value in row
            ]
            for row in table.rows
        ]

        self._validate_table(
            columns,
            normalized_rows,
        )

        widths = (
            self._calculate_column_widths(
                columns,
                normalized_rows,
            )
        )

        header = self._format_table_row(
            columns,
            widths,
        )

        separator = (
            self._format_table_separator(
                widths
            )
        )

        rows = [
            self._format_table_row(
                row,
                widths,
            )
            for row in normalized_rows
        ]

        return "\n".join(
            [
                "Data",
                self.render_divider(),
                header,
                separator,
                *rows,
            ]
        )

    def render_tree(
        self,
        tree: TreeModel,
    ) -> str:
        """
        Path Tree 또는 Logical Tree Section을 생성한다.
        """

        title = tree.title.strip()

        if not title:
            raise ValueError(
                "Tree title must not be empty."
            )

        if tree.root is not None:
            content = TreeFormatter.render_node(
                tree.root
            )

        else:
            content = TreeFormatter.render(
                paths=tree.paths,
                root_name=tree.root_name,
            )

        return "\n".join(
            [
                title,
                self.render_divider(),
                content,
            ]
        )

    def render_footer(
        self,
        status: str,
    ) -> str:
        """공통 Footer를 생성한다."""

        normalized_status = (
            status.upper()
        )

        rendered_status = (
            self._resolve_status_text(
                normalized_status
            )
        )

        rendered_dt = (
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        return "\n".join(
            [
                self.render_divider(),
                rendered_status,
                rendered_dt,
                self.render_divider(),
            ]
        )

    def render_divider(self) -> str:
        """공통 구분선을 생성한다."""

        return (
            self.config.divider_character
            * self.config.width
        )

    def _calculate_column_widths(
        self,
        columns: Sequence[str],
        rows: Sequence[Sequence[str]],
    ) -> list[int]:
        widths = [
            len(column)
            for column in columns
        ]

        for row in rows:
            for index, value in enumerate(row):
                widths[index] = max(
                    widths[index],
                    len(value),
                )

        return widths

    def _format_table_row(
        self,
        row: Sequence[str],
        widths: Sequence[int],
    ) -> str:
        cells = [
            value.ljust(
                widths[index]
            )
            for index, value in enumerate(row)
        ]

        return (
            self.config.table_column_separator
            .join(cells)
        )

    def _format_table_separator(
        self,
        widths: Sequence[int],
    ) -> str:
        separator_token = "-+-"

        return separator_token.join(
            "-" * width
            for width in widths
        )

    def _validate_table(
        self,
        columns: Sequence[str],
        rows: Sequence[Sequence[str]],
    ) -> None:
        column_count = len(columns)

        if column_count == 0:
            raise ValueError(
                "Table columns must not be empty."
            )

        for row_no, row in enumerate(
            rows,
            start=1,
        ):
            if len(row) != column_count:
                raise ValueError(
                    "Table row column count mismatch: "
                    f"row_no={row_no}, "
                    f"expected={column_count}, "
                    f"actual={len(row)}"
                )

    def _normalize_value(
        self,
        value: Any,
    ) -> str:
        if value is None:
            return self.config.empty_value

        if isinstance(value, bool):
            return (
                "Y"
                if value
                else "N"
            )

        return str(value)

    def _resolve_status_text(
        self,
        status: str,
    ) -> str:
        status_mapping = {
            "SUCCESS": self.config.success_text,
            "WARNING": self.config.warning_text,
            "ERROR": self.config.error_text,
            "INFO": self.config.info_text,
        }

        return status_mapping.get(
            status,
            status,
        )
