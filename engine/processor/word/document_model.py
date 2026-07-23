"""
SPS Word Document Model

Purpose:
    Repository Metadata와 조회 데이터를 Word 출력 형식과 분리된
    중립적인 Document Model로 표현한다.

Principles:
    - Repository First
    - Generator First
    - Metadata Driven
    - Single Source of Truth
    - No Hardcoding
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping


@dataclass(slots=True)
class DocumentParagraph:
    """문서의 일반 문단을 표현한다."""

    text: str
    bold: bool = False
    italic: bool = False
    alignment: str = "LEFT"

    def __post_init__(self) -> None:
        self.text = str(self.text)
        self.alignment = self.alignment.strip().upper()

        supported_alignments = {
            "LEFT",
            "CENTER",
            "RIGHT",
            "JUSTIFY",
        }

        if self.alignment not in supported_alignments:
            raise ValueError(
                "Unsupported paragraph alignment: "
                f"{self.alignment}. "
                f"Supported values: {sorted(supported_alignments)}"
            )


@dataclass(slots=True)
class DocumentHeading:
    """문서 제목 또는 절 제목을 표현한다."""

    text: str
    level: int = 1

    def __post_init__(self) -> None:
        self.text = str(self.text).strip()

        if not self.text:
            raise ValueError("Heading text must not be empty.")

        if self.level < 1 or self.level > 9:
            raise ValueError(
                "Heading level must be between 1 and 9."
            )


@dataclass(slots=True)
class DocumentTable:
    """문서에 출력할 표를 표현한다."""

    headers: list[str]
    rows: list[list[str]]
    title: str | None = None
    style_name: str = "Table Grid"
    repeat_header: bool = True
    autofit: bool = True

    def __post_init__(self) -> None:
        self.headers = [
            self._normalize_cell_value(value)
            for value in self.headers
        ]

        self.rows = [
            [
                self._normalize_cell_value(value)
                for value in row
            ]
            for row in self.rows
        ]

        if not self.headers:
            raise ValueError(
                "DocumentTable must contain at least one header."
            )

        header_count = len(self.headers)

        for row_index, row in enumerate(self.rows, start=1):
            if len(row) != header_count:
                raise ValueError(
                    "Table row column count does not match headers. "
                    f"row_index={row_index}, "
                    f"expected={header_count}, "
                    f"actual={len(row)}"
                )

        if self.title is not None:
            self.title = str(self.title).strip() or None

        self.style_name = str(self.style_name).strip()

        if not self.style_name:
            raise ValueError(
                "Table style_name must not be empty."
            )

    @staticmethod
    def _normalize_cell_value(value: Any) -> str:
        """표 Cell 값을 안전한 문자열로 변환한다."""

        if value is None:
            return ""

        if isinstance(value, bool):
            return "Y" if value else "N"

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")

        if isinstance(value, Decimal):
            return format(value, "f")

        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")

        return str(value)


@dataclass(slots=True)
class DocumentMetadata:
    """생성 문서의 관리 Metadata를 표현한다."""

    document_name: str
    source_object_code: str
    artifact_type_code: str = "WORD"
    processor_code: str = "WORD_DOCUMENT_PROCESSOR"
    description: str | None = None
    generated_dt: datetime = field(
        default_factory=datetime.now
    )
    attributes: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.document_name = self.document_name.strip()
        self.source_object_code = (
            self.source_object_code.strip().upper()
        )
        self.artifact_type_code = (
            self.artifact_type_code.strip().upper()
        )
        self.processor_code = (
            self.processor_code.strip().upper()
        )

        if not self.document_name:
            raise ValueError(
                "document_name must not be empty."
            )

        if not self.source_object_code:
            raise ValueError(
                "source_object_code must not be empty."
            )

        if not self.artifact_type_code:
            raise ValueError(
                "artifact_type_code must not be empty."
            )

        if not self.processor_code:
            raise ValueError(
                "processor_code must not be empty."
            )

        if self.description is not None:
            self.description = (
                str(self.description).strip() or None
            )


DocumentBlock = (
    DocumentParagraph
    | DocumentHeading
    | DocumentTable
)


@dataclass(slots=True)
class DocumentModel:
    """
    Word Renderer가 소비하는 중립 Document Model.

    Renderer 전용 객체를 포함하지 않으므로 PDF, HTML 등의
    Processor에서도 동일한 모델을 재사용할 수 있다.
    """

    title: str
    metadata: DocumentMetadata
    blocks: list[DocumentBlock] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.title = self.title.strip()

        if not self.title:
            raise ValueError(
                "Document title must not be empty."
            )

    def add_heading(
        self,
        text: str,
        level: int = 1,
    ) -> DocumentModel:
        """Heading Block을 추가한다."""

        self.blocks.append(
            DocumentHeading(
                text=text,
                level=level,
            )
        )

        return self

    def add_numbered_heading(
        self,
        text: str,
        level: int = 1,
        heading_label: str | None = None,
    ) -> DocumentModel:
        """계층 번호를 자동 생성하여 Heading Block을 추가한다."""

        normalized_level = int(level)

        if normalized_level < 1 or normalized_level > 9:
            raise ValueError(
                "Heading level must be between 1 and 9."
            )

        counters = self.metadata.attributes.setdefault(
            "_heading_counters",
            [0] * 9,
        )
        counters[normalized_level - 1] += 1

        for index in range(normalized_level, 9):
            counters[index] = 0

        number_tokens = [
            str(counter)
            for counter in counters[:normalized_level]
            if counter > 0
        ]
        heading_number = ".".join(number_tokens)

        normalized_label = (heading_label or "").strip()
        heading_text = (
            f"{normalized_label} {heading_number}. {text}"
            if normalized_label
            else f"{heading_number}. {text}"
        )

        return self.add_heading(
            text=heading_text,
            level=normalized_level,
        )

    def add_paragraph(
        self,
        text: str,
        *,
        bold: bool = False,
        italic: bool = False,
        alignment: str = "LEFT",
    ) -> DocumentModel:
        """Paragraph Block을 추가한다."""

        self.blocks.append(
            DocumentParagraph(
                text=text,
                bold=bold,
                italic=italic,
                alignment=alignment,
            )
        )

        return self

    def add_table(
        self,
        headers: Iterable[Any],
        rows: Iterable[Iterable[Any]],
        *,
        title: str | None = None,
        style_name: str = "Table Grid",
        repeat_header: bool = True,
        autofit: bool = True,
    ) -> DocumentModel:
        """Table Block을 추가한다."""

        self.blocks.append(
            DocumentTable(
                headers=[
                    DocumentTable._normalize_cell_value(value)
                    for value in headers
                ],
                rows=[
                    [
                        DocumentTable._normalize_cell_value(value)
                        for value in row
                    ]
                    for row in rows
                ],
                title=title,
                style_name=style_name,
                repeat_header=repeat_header,
                autofit=autofit,
            )
        )

        return self

    @classmethod
    def from_repository_rows(
        cls,
        *,
        title: str,
        document_name: str,
        source_object_code: str,
        rows: Iterable[Mapping[str, Any]],
        columns: Iterable[str] | None = None,
        description: str | None = None,
        processor_code: str = "WORD_DOCUMENT_PROCESSOR",
    ) -> DocumentModel:
        """
        Repository 조회 결과를 표 중심 Document Model로 변환한다.

        rows:
            CommonDatabase.fetch_all()이 반환하는
            list[dict] 형태를 직접 전달할 수 있다.

        columns:
            출력할 컬럼 순서를 지정한다.
            생략하면 첫 번째 Row의 Key 순서를 사용한다.
        """

        normalized_rows = [
            dict(row)
            for row in rows
        ]

        if columns is None:
            resolved_columns = (
                list(normalized_rows[0].keys())
                if normalized_rows
                else []
            )
        else:
            resolved_columns = [
                str(column).strip()
                for column in columns
                if str(column).strip()
            ]

        metadata = DocumentMetadata(
            document_name=document_name,
            source_object_code=source_object_code,
            artifact_type_code="WORD",
            processor_code=processor_code,
            description=description,
            attributes={
                "row_count": len(normalized_rows),
                "column_count": len(resolved_columns),
            },
        )

        model = cls(
            title=title,
            metadata=metadata,
        )

        if description:
            model.add_paragraph(description)

        model.add_paragraph(
            (
                f"Source Object: {source_object_code} / "
                f"Rows: {len(normalized_rows)} / "
                f"Columns: {len(resolved_columns)}"
            )
        )

        if not resolved_columns:
            model.add_paragraph(
                "출력할 Repository 데이터가 없습니다."
            )
            return model

        table_rows = [
            [
                row.get(column)
                for column in resolved_columns
            ]
            for row in normalized_rows
        ]

        model.add_table(
            headers=resolved_columns,
            rows=table_rows,
            title=source_object_code,
        )

        return model
