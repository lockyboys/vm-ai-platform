"""SPS Repository Table Schema Word Processor."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from common.database import CommonDatabase
from engine.processor.word.document_model import (
    DocumentMetadata,
    DocumentModel,
)
from engine.processor.word.word_writer import WordWriter


class WordDocumentProcessor:
    """Repository Table을 Schema Word Artifact로 생성한다."""

    DEFAULT_DATABASE_ROLE = "COMMON"
    DEFAULT_SAMPLE_LIMIT = 5

    VALID_IDENTIFIER_PATTERN = re.compile(
        r"^[A-Za-z_][A-Za-z0-9_]*$"
    )

    def __init__(
        self,
        database_role: str = DEFAULT_DATABASE_ROLE,
        database: CommonDatabase | None = None,
    ) -> None:
        self.database_role = database_role.strip().upper()

        self.database = (
            database
            if database is not None
            else CommonDatabase(database_role=self.database_role)
        )

        self.writer = WordWriter()

    def generate_table_document(
        self,
        table_name: str,
        output_path: str | Path,
        sample_limit: int = DEFAULT_SAMPLE_LIMIT,
    ) -> Path:
        """Table Schema와 Sample Data를 Word로 생성한다."""

        normalized_table_name = self._validate_table_name(
            table_name
        )
        normalized_sample_limit = self._validate_sample_limit(
            sample_limit
        )

        columns = self._load_columns(normalized_table_name)
        create_table_sql = self._load_create_table(
            normalized_table_name
        )
        sample_rows = self._load_sample_rows(
            normalized_table_name,
            normalized_sample_limit,
        )

        model = self._build_table_schema_model(
            table_name=normalized_table_name,
            columns=columns,
            create_table_sql=create_table_sql,
            sample_rows=sample_rows,
            sample_limit=normalized_sample_limit,
        )

        return self.writer.save(
            model=model,
            output_path=output_path,
        )

    def _load_columns(
        self,
        table_name: str,
    ) -> list[dict[str, Any]]:
        sql = f"SHOW FULL COLUMNS FROM `{table_name}`"

        return self.database.fetch_all(sql)

    def _load_create_table(
        self,
        table_name: str,
    ) -> str:
        sql = f"SHOW CREATE TABLE `{table_name}`"
        row = self.database.fetch_one(sql)

        if not row:
            raise ValueError(
                f"Table was not found: {table_name}"
            )

        create_table_sql = row.get("Create Table")

        if not create_table_sql:
            raise ValueError(
                f"CREATE TABLE metadata was not found: {table_name}"
            )

        return str(create_table_sql)

    def _load_sample_rows(
        self,
        table_name: str,
        sample_limit: int,
    ) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM `{table_name}` LIMIT %s"

        return self.database.fetch_all(
            sql,
            (sample_limit,),
        )

    def _build_table_schema_model(
        self,
        *,
        table_name: str,
        columns: list[dict[str, Any]],
        create_table_sql: str,
        sample_rows: list[dict[str, Any]],
        sample_limit: int,
    ) -> DocumentModel:
        metadata = DocumentMetadata(
            document_name=f"{table_name}_schema",
            source_object_code=table_name.upper(),
            description=(
                "Repository Table Schema Word Artifact"
            ),
            attributes={
                "database_role": self.database_role,
                "database_name": self.database.database_name,
                "table_name": table_name,
                "column_count": len(columns),
                "sample_limit": sample_limit,
            },
        )

        model = DocumentModel(
            title=f"{table_name} Schema Document",
            metadata=metadata,
        )

        self._add_overview(
            model=model,
            table_name=table_name,
            columns=columns,
            sample_rows=sample_rows,
        )
        self._add_column_schema(
            model=model,
            columns=columns,
        )
        self._add_primary_key(
            model=model,
            columns=columns,
        )
        self._add_constraints(
            model=model,
            create_table_sql=create_table_sql,
        )
        self._add_sample_data(
            model=model,
            columns=columns,
            sample_rows=sample_rows,
        )
        self._add_create_table(
            model=model,
            create_table_sql=create_table_sql,
        )

        return model

    def _add_overview(
        self,
        *,
        model: DocumentModel,
        table_name: str,
        columns: list[dict[str, Any]],
        sample_rows: list[dict[str, Any]],
    ) -> None:
        model.add_heading(
            "1. Table Object Overview",
            level=1,
        )
        model.add_table(
            headers=["Property", "Value"],
            rows=[
                ["Database Role", self.database_role],
                ["Database", self.database.database_name],
                ["Table Object", table_name],
                ["Column Count", len(columns)],
                ["Sample Row Count", len(sample_rows)],
            ],
            title="Table Object",
        )

    @staticmethod
    def _add_column_schema(
        *,
        model: DocumentModel,
        columns: list[dict[str, Any]],
    ) -> None:
        model.add_heading(
            "2. Column Schema",
            level=1,
        )

        headers = [
            "Field",
            "Type",
            "Null",
            "Key",
            "Default",
            "Extra",
            "Comment",
        ]

        rows = [
            [
                column.get("Field"),
                column.get("Type"),
                column.get("Null"),
                column.get("Key"),
                column.get("Default"),
                column.get("Extra"),
                column.get("Comment"),
            ]
            for column in columns
        ]

        model.add_table(
            headers=headers,
            rows=rows,
            title="Column Schema",
        )

    @staticmethod
    def _add_primary_key(
        *,
        model: DocumentModel,
        columns: list[dict[str, Any]],
    ) -> None:
        model.add_heading(
            "3. Primary Key",
            level=1,
        )

        primary_key_columns = [
            str(column.get("Field"))
            for column in columns
            if column.get("Key") == "PRI"
        ]

        if primary_key_columns:
            model.add_paragraph(
                " + ".join(primary_key_columns)
            )
        else:
            model.add_paragraph(
                "Primary Key가 정의되지 않았습니다."
            )

    @staticmethod
    def _add_constraints(
        *,
        model: DocumentModel,
        create_table_sql: str,
    ) -> None:
        model.add_heading(
            "4. Constraints",
            level=1,
        )

        constraint_lines = [
            line.strip().rstrip(",")
            for line in create_table_sql.splitlines()
            if (
                "CONSTRAINT " in line.upper()
                or " CHECK " in line.upper()
            )
        ]

        if not constraint_lines:
            model.add_paragraph(
                "별도 Constraint가 정의되지 않았습니다."
            )
            return

        for constraint_line in constraint_lines:
            model.add_paragraph(constraint_line)

    @staticmethod
    def _add_sample_data(
        *,
        model: DocumentModel,
        columns: list[dict[str, Any]],
        sample_rows: list[dict[str, Any]],
    ) -> None:
        model.add_heading(
            "5. Sample Data",
            level=1,
        )

        column_names = [
            str(column.get("Field"))
            for column in columns
        ]

        if not sample_rows:
            model.add_paragraph(
                "조회된 Sample Data가 없습니다."
            )
            return

        rows = [
            [
                row.get(column_name)
                for column_name in column_names
            ]
            for row in sample_rows
        ]

        model.add_table(
            headers=column_names,
            rows=rows,
            title="Repository Sample Data",
        )

    @staticmethod
    def _add_create_table(
        *,
        model: DocumentModel,
        create_table_sql: str,
    ) -> None:
        model.add_heading(
            "6. CREATE TABLE",
            level=1,
        )
        model.add_paragraph(create_table_sql)

    @classmethod
    def _validate_table_name(
        cls,
        table_name: str,
    ) -> str:
        normalized_table_name = table_name.strip()

        if not normalized_table_name:
            raise ValueError(
                "table_name must not be empty."
            )

        if not cls.VALID_IDENTIFIER_PATTERN.fullmatch(
            normalized_table_name
        ):
            raise ValueError(
                "table_name contains invalid characters."
            )

        return normalized_table_name

    @staticmethod
    def _validate_sample_limit(
        sample_limit: int,
    ) -> int:
        if isinstance(sample_limit, bool):
            raise TypeError(
                "sample_limit must be an integer."
            )

        try:
            normalized_sample_limit = int(sample_limit)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                "sample_limit must be an integer."
            ) from exc

        if normalized_sample_limit < 1:
            raise ValueError(
                "sample_limit must be greater than zero."
            )

        return normalized_sample_limit
