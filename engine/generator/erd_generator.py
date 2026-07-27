"""
SPS ERD Generator

Purpose:
    Repository Database Schema를 읽어 Table, Column, PK, FK 기반 ERD Model을
    생성하고 Mermaid ERD 문서로 출력한다.

Principles:
    - Repository First
    - Generator First
    - Metadata Driven
    - Single Source of Truth
    - No Hardcoding
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from common.database import CommonDatabase
from engine.identifier_engine import IdentifierEngine
from engine.object_definition_engine import ObjectDefinitionEngine


@dataclass(frozen=True, slots=True)
class ErdColumn:
    """ERD Column Metadata."""

    column_name: str
    data_type: str
    nullable_yn: str
    primary_key_yn: str
    unique_key_yn: str
    column_comment: str | None


@dataclass(frozen=True, slots=True)
class ErdTable:
    """ERD Table Metadata."""

    table_name: str
    table_comment: str | None
    columns: tuple[ErdColumn, ...]


@dataclass(frozen=True, slots=True)
class ErdRelationship:
    """ERD Foreign Key Relationship Metadata."""

    constraint_name: str
    source_table: str
    source_column: str
    target_table: str
    target_column: str


@dataclass(frozen=True, slots=True)
class ErdModel:
    """Repository에서 해석한 ERD Model."""

    database_role: str
    database_name: str
    tables: tuple[ErdTable, ...]
    relationships: tuple[ErdRelationship, ...]


@dataclass(frozen=True, slots=True)
class ErdGenerationResult:
    """ERD 생성 결과."""

    model: ErdModel
    mermaid_text: str
    output_path: Path | None
    erd_repository_row: dict[str, Any] | None


class ErdGenerator:
    """MariaDB Repository Schema 기반 Mermaid ERD Generator."""

    OBJECT_CODE = "ERD"
    METADATA_OBJECT_CODE = "METADATA"
    METADATA_TARGET_TYPE_CODE = "GENERATOR"
    METADATA_TYPE_CODE = "ERD_RULE"
    PROGRAM_ID = "erd_generator.py"
    SAFE_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

    def __init__(
        self,
        database: CommonDatabase,
        *,
        repository_database: CommonDatabase | None = None,
    ) -> None:
        self.database = database
        self.repository_database = repository_database or CommonDatabase(
            database_role="STORY_PLATFORM"
        )

    def generate(
        self,
        *,
        table_names: Iterable[str] | None = None,
        relationship_expansion_depth: int = 0,
        include_logical_relations_yn: str = "N",
        output_path: str | Path | None = None,
        register_repository_yn: str = "N",
        erd_code: str | None = None,
        erd_name: str | None = None,
        business_code: str | None = None,
        domain_code: str | None = None,
        erd_description: str | None = None,
        created_by: str = "SYSTEM",
        client_ip: str = "127.0.0.1",
    ) -> ErdGenerationResult:
        """Repository Schema를 ERD Model과 Mermaid 문서로 생성한다."""
        self._ensure_object_sequence_metadata(self.METADATA_OBJECT_CODE)
        self._ensure_object_sequence_metadata("RELATIONSHIP")
        self._ensure_erd_rule_metadata(created_by, client_ip)
        normalized_table_names = self._normalize_table_names(table_names)
        expanded_table_names = self._expand_table_names(
            normalized_table_names,
            relationship_expansion_depth=relationship_expansion_depth,
            include_logical_relations_yn=include_logical_relations_yn,
        )
        self._sync_physical_fk_relationships(
            expanded_table_names,
            created_by,
            client_ip,
        )
        model = self._load_model(expanded_table_names)
        mermaid_text = self.render_mermaid(model)

        resolved_output_path = None
        if output_path is not None:
            resolved_output_path = Path(output_path).resolve()
            resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
            resolved_output_path.write_text(mermaid_text, encoding="utf-8")

        repository_row = None
        if str(register_repository_yn).strip().upper() == "Y":
            repository_row = self._register_repository(
                erd_code=erd_code,
                erd_name=erd_name,
                business_code=business_code,
                domain_code=domain_code,
                erd_description=erd_description,
                created_by=created_by,
                client_ip=client_ip,
            )

        return ErdGenerationResult(
            model=model,
            mermaid_text=mermaid_text,
            output_path=resolved_output_path,
            erd_repository_row=repository_row,
        )

    def _ensure_object_sequence_metadata(self, object_code: str) -> None:
        """기존 Object 정의를 재사용해 현재 Sequence Metadata를 보장한다."""
        row = self.repository_database.fetch_one(
            """
            SELECT
                object_code,
                object_name,
                business_code,
                domain_code,
                object_type_code,
                object_level,
                identifier_target_code,
                sequence_scope_code,
                sequence_length,
                target_identifier_field
            FROM sp_object
            WHERE object_code = %s
              AND active_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (object_code,),
        )
        if not row:
            raise ValueError(f"Object not found: object_code={object_code}")

        ObjectDefinitionEngine(self.repository_database).create(dict(row))

    def _load_model(self, table_names: tuple[str, ...] | None) -> ErdModel:
        excluded_columns = self._load_metadata_excluded_columns()
        table_rows = self._load_tables(table_names)
        column_rows = self._load_columns(table_names)
        relationship_rows = self._load_relationships(table_names)

        foreign_key_columns = {
            (row["source_table"], row["source_column"])
            for row in relationship_rows
        } | {
            (row["target_table"], row["target_column"])
            for row in relationship_rows
        }

        column_rows = [
            row
            for row in column_rows
            if not (
                (row["table_name"], row["column_name"])
                in excluded_columns
                and row["column_key"] != "PRI"
                and (row["table_name"], row["column_name"])
                not in foreign_key_columns
            )
        ]

        columns_by_table: dict[str, list[ErdColumn]] = {}
        for row in column_rows:
            columns_by_table.setdefault(row["table_name"], []).append(
                ErdColumn(
                    column_name=row["column_name"],
                    data_type=row["column_type"],
                    nullable_yn="Y" if row["is_nullable"] == "YES" else "N",
                    primary_key_yn="Y" if row["column_key"] == "PRI" else "N",
                    unique_key_yn="Y" if row["column_key"] == "UNI" else "N",
                    column_comment=row.get("column_comment") or None,
                )
            )

        table_scope_map = self._load_table_scope_map(column_rows)
        table_rows = self._order_tables_for_layout(
            table_rows,
            relationship_rows,
            table_scope_map,
        )
        tables = tuple(
            ErdTable(
                table_name=row["table_name"],
                table_comment=row.get("table_comment") or None,
                columns=tuple(columns_by_table.get(row["table_name"], [])),
            )
            for row in table_rows
        )

        relationships = tuple(
            ErdRelationship(
                constraint_name=row["constraint_name"],
                source_table=row["source_table"],
                source_column=row["source_column"],
                target_table=row["target_table"],
                target_column=row["target_column"],
            )
            for row in relationship_rows
        )

        return ErdModel(
            database_role=self.database.database_role,
            database_name=self.database.database_name,
            tables=tables,
            relationships=relationships,
        )

    def _load_tables(self, table_names: tuple[str, ...] | None) -> list[dict[str, Any]]:
        condition_sql, params = self._build_table_filter("table_name", table_names)
        return self.database.fetch_all(
            f"""
            SELECT table_name, table_comment
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
              {condition_sql}
            ORDER BY table_name
            """,
            (self.database.database_name, *params),
        )

    def _load_columns(self, table_names: tuple[str, ...] | None) -> list[dict[str, Any]]:
        condition_sql, params = self._build_table_filter("table_name", table_names)
        return self.database.fetch_all(
            f"""
            SELECT
                table_name,
                column_name,
                column_type,
                is_nullable,
                column_key,
                column_comment,
                ordinal_position
            FROM information_schema.columns
            WHERE table_schema = %s
              {condition_sql}
            ORDER BY table_name, ordinal_position
            """,
            (self.database.database_name, *params),
        )

    def _load_relationships(
        self,
        table_names: tuple[str, ...] | None,
    ) -> list[dict[str, Any]]:
        condition_sql = ""
        params: tuple[Any, ...] = ()
        if table_names:
            placeholders = ", ".join(["%s"] * len(table_names))
            condition_sql = (
                f"AND kcu.table_name IN ({placeholders}) "
                f"AND kcu.referenced_table_name IN ({placeholders})"
            )
            params = (*table_names, *table_names)

        return self.database.fetch_all(
            f"""
            SELECT
                kcu.constraint_name,
                kcu.table_name AS source_table,
                kcu.column_name AS source_column,
                kcu.referenced_table_name AS target_table,
                kcu.referenced_column_name AS target_column
            FROM information_schema.key_column_usage kcu
            WHERE kcu.table_schema = %s
              AND kcu.referenced_table_name IS NOT NULL
              {condition_sql}
            ORDER BY
                kcu.table_name,
                kcu.constraint_name,
                kcu.ordinal_position
            """,
            (self.database.database_name, *params),
        )

    @classmethod
    def render_mermaid(cls, model: ErdModel) -> str:
        """ERD Model을 Mermaid erDiagram 문서로 변환한다."""
        lines = [
            "---",
            f"title: {model.database_name} ERD",
            "---",
            "erDiagram",
        ]

        for table in model.tables:
            lines.append(f"    {cls._safe_mermaid_name(table.table_name)} {{")
            for column in table.columns:
                key_markers = []
                if column.primary_key_yn == "Y":
                    key_markers.append("PK")
                if column.unique_key_yn == "Y":
                    key_markers.append("UK")
                key_text = f" {' '.join(key_markers)}" if key_markers else ""
                nullable_text = "nullable" if column.nullable_yn == "Y" else ""
                description_text = (
                    f' "{nullable_text}"'
                    if nullable_text
                    else ""
                )
                lines.append(
                    "        "
                    f"{cls._safe_mermaid_type(column.data_type)} "
                    f"{cls._safe_mermaid_name(column.column_name)}"
                    f"{key_text}"
                    f"{description_text}"
                )
            lines.append("    }")

        for relationship in model.relationships:
            source = cls._safe_mermaid_name(relationship.source_table)
            target = cls._safe_mermaid_name(relationship.target_table)
            label = (
                f"{relationship.source_column}→{relationship.target_column}"
            )
            lines.append(f'    {target} ||--o{{ {source} : "{label}"')

        return "\n".join(lines) + "\n"

    def _register_repository(
        self,
        *,
        erd_code: str | None,
        erd_name: str | None,
        business_code: str | None,
        domain_code: str | None,
        erd_description: str | None,
        created_by: str,
        client_ip: str,
    ) -> dict[str, Any]:
        required = {
            "erd_code": erd_code,
            "erd_name": erd_name,
            "business_code": business_code,
            "domain_code": domain_code,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(f"ERD Repository fields are required: {missing}")

        normalized_erd_code = str(erd_code).strip().upper()
        if not self.SAFE_CODE_PATTERN.fullmatch(normalized_erd_code):
            raise ValueError(f"Invalid erd_code: {erd_code}")

        existing = self.repository_database.fetch_one(
            """
            SELECT erd_id, erd_code, erd_name, business_code, domain_code
            FROM sp_erd
            WHERE erd_code = %s
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (normalized_erd_code,),
        )
        if existing:
            return existing

        identifier_engine = IdentifierEngine(self.repository_database)
        erd_id = identifier_engine.generate(self.OBJECT_CODE)

        self.repository_database.begin()
        try:
            affected = self.repository_database.execute(
                """
                INSERT INTO sp_erd
                (
                    erd_id, erd_code, erd_name,
                    business_code, domain_code, erd_description,
                    enabled_yn, sort_no,
                    created_by, updated_by, client_ip, program_id
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, 'Y', 0, %s, %s, %s, %s)
                """,
                (
                    erd_id,
                    normalized_erd_code,
                    str(erd_name).strip(),
                    str(business_code).strip().upper(),
                    str(domain_code).strip().upper(),
                    erd_description,
                    created_by,
                    created_by,
                    client_ip,
                    self.PROGRAM_ID,
                ),
            )
            if affected != 1:
                raise RuntimeError(f"sp_erd insert failed: affected_rows={affected}")
            self.repository_database.commit()
        except Exception:
            self.repository_database.rollback()
            raise

        saved = self.repository_database.fetch_one(
            """
            SELECT erd_id, erd_code, erd_name, business_code, domain_code
            FROM sp_erd
            WHERE erd_id = %s
            """,
            (erd_id,),
        )
        if not saved:
            raise RuntimeError(f"sp_erd verification failed: erd_id={erd_id}")
        return saved

    def _ensure_erd_rule_metadata(
        self,
        created_by: str,
        client_ip: str,
    ) -> None:
        """기존 METADATA Object ID에 ERD Generator 규칙을 멱등 등록한다."""
        target_row = self.repository_database.fetch_one(
            """
            SELECT object_id
            FROM sp_object
            WHERE object_code = %s
              AND active_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (self.METADATA_OBJECT_CODE,),
        )
        if not target_row:
            raise ValueError("Metadata Object not found.")

        target_id = target_row["object_id"]
        exists = self.repository_database.fetch_one(
            """
            SELECT metadata_id
            FROM sp_metadata
            WHERE target_type_code = %s
              AND target_id = %s
              AND metadata_key = 'ERD_GENERATOR_RULES'
              AND enabled_yn = 'Y'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (self.METADATA_TARGET_TYPE_CODE, target_id),
        )
        if exists:
            return

        rule_json = {
            "column_exclusion": {
                "marker": "[제외]",
                "scope": "NON_KEY_COLUMN_ONLY",
                "preserve_primary_key": True,
                "preserve_foreign_key": True,
                "preserve_relationship": True,
            },
            "layout": {
                "scope": "BUSINESS_DOMAIN",
                "scope_source": "SP_OBJECT",
                "center_table_first": True,
                "prefix_inference_allowed": False,
            },
            "relation_line": {
                "crossing_policy": "MINIMIZE",
                "overlap_policy": "MINIMIZE",
            },
        }

        identifier_engine = IdentifierEngine(self.repository_database)
        try:
            self.repository_database.begin()
            metadata_id = identifier_engine.generate(
                self.METADATA_OBJECT_CODE,
                manage_transaction=False,
            )
            self.repository_database.execute(
                """
                INSERT INTO sp_metadata
                (
                    metadata_id, target_type_code, target_id,
                    metadata_type_code, metadata_key, metadata_value,
                    metadata_value_type_code, metadata_json,
                    enabled_yn, sort_no,
                    created_by, updated_by, client_ip, program_id
                )
                VALUES
                (%s, %s, %s, %s, 'ERD_GENERATOR_RULES',
                 'ERD Generator 공통 생성 규칙', 'JSON', %s,
                 'Y', 10, %s, %s, %s, %s)
                """,
                (
                    metadata_id,
                    self.METADATA_TARGET_TYPE_CODE,
                    target_id,
                    self.METADATA_TYPE_CODE,
                    json.dumps(rule_json, ensure_ascii=False),
                    created_by,
                    created_by,
                    client_ip,
                    self.PROGRAM_ID,
                ),
            )
            self.repository_database.commit()
        except Exception:
            self.repository_database.rollback()
            raise

    def _sync_physical_fk_relationships(
        self,
        table_names: Iterable[str] | None,
        created_by: str,
        client_ip: str,
    ) -> None:
        """물리 FK를 기존 Table Object 사이의 OBJECT 관계로 동기화한다."""
        normalized_table_names = self._normalize_table_names(table_names)
        relationship_rows = self._load_relationships(normalized_table_names)
        if not relationship_rows:
            return

        column_rows = self._load_columns(normalized_table_names)
        primary_key_by_table = {
            row["table_name"]: row["column_name"]
            for row in column_rows
            if row["column_key"] == "PRI"
        }
        nullable_by_column = {
            (row["table_name"], row["column_name"]): row["is_nullable"]
            for row in column_rows
        }
        object_rows = self.repository_database.fetch_all(
            """
            SELECT object_id, target_identifier_field
            FROM sp_object
            WHERE object_type_code = 'TABLE'
              AND active_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
              AND target_identifier_field IS NOT NULL
            """
        )
        object_id_by_primary_key = {
            row["target_identifier_field"]: row["object_id"]
            for row in object_rows
        }
        object_id_by_table = {
            table_name: object_id_by_primary_key.get(primary_key)
            for table_name, primary_key in primary_key_by_table.items()
        }

        self._insert_missing_physical_fk_relationships(
            relationship_rows=relationship_rows,
            primary_key_by_table=primary_key_by_table,
            nullable_by_column=nullable_by_column,
            object_id_by_table=object_id_by_table,
            created_by=created_by,
            client_ip=client_ip,
        )

    def _insert_missing_physical_fk_relationships(
        self,
        *,
        relationship_rows: list[dict[str, Any]],
        primary_key_by_table: dict[str, str],
        nullable_by_column: dict[tuple[str, str], str],
        object_id_by_table: dict[str, str | None],
        created_by: str,
        client_ip: str,
    ) -> None:
        """해석 가능한 물리 FK만 sp_relationship에 멱등 저장한다."""
        identifier_engine = IdentifierEngine(self.repository_database)
        self.repository_database.begin()
        try:
            for sort_no, row in enumerate(relationship_rows, start=1):
                source_object_id = object_id_by_table.get(row["source_table"])
                target_object_id = object_id_by_table.get(row["target_table"])
                if not source_object_id or not target_object_id:
                    continue

                relationship_code = self._physical_fk_relationship_code(row)
                exists = self.repository_database.fetch_one(
                    """
                    SELECT relationship_id
                    FROM sp_relationship
                    WHERE relationship_code = %s
                      AND deleted_dt IS NULL
                    LIMIT 1
                    """,
                    (relationship_code,),
                )
                if exists:
                    continue

                relationship_id = identifier_engine.generate_for_level(
                    object_code="RELATIONSHIP",
                    object_level=3,
                    manage_transaction=False,
                )
                identifying_yn = (
                    "Y"
                    if primary_key_by_table.get(row["source_table"])
                    == row["source_column"]
                    else "N"
                )
                source_min_cardinality = (
                    0
                    if nullable_by_column.get(
                        (row["source_table"], row["source_column"])
                    ) == "YES"
                    else 1
                )

                self.repository_database.execute(
                    """
                    INSERT INTO sp_relationship
                    (
                        relationship_id, relationship_scope_code,
                        source_object_id, source_object_type_code,
                        target_object_id, target_object_type_code,
                        relationship_code, relationship_name,
                        relationship_description, relationship_type_code,
                        source_min_cardinality, source_max_cardinality,
                        target_min_cardinality, target_max_cardinality,
                        identifying_yn, enabled_yn, sort_no,
                        created_by, updated_by, client_ip, program_id
                    )
                    VALUES
                    (%s, 'OBJECT', %s, 'TABLE', %s, 'TABLE', %s, %s, %s, 'FK',
                     %s, 1, 0, -1, %s, 'Y', %s, %s, %s, %s, %s)
                    """,
                    (
                        relationship_id,
                        source_object_id,
                        target_object_id,
                        relationship_code,
                        f"{row['source_table']} FK {row['target_table']}",
                        f"{row['source_table']}.{row['source_column']} -> "
                        f"{row['target_table']}.{row['target_column']}",
                        source_min_cardinality,
                        identifying_yn,
                        sort_no,
                        created_by,
                        created_by,
                        client_ip,
                        self.PROGRAM_ID,
                    ),
                )
            self.repository_database.commit()
        except Exception:
            self.repository_database.rollback()
            raise

    def _physical_fk_relationship_code(self, row: dict[str, Any]) -> str:
        """물리 FK Constraint를 안정적인 Relationship Code로 변환한다."""
        raw_code = (
            f"PHYSICAL_FK_{self.database.database_name}_"
            f"{row['constraint_name']}"
        ).upper()
        normalized = re.sub(r"[^A-Z0-9_]", "_", raw_code)
        if len(normalized) <= 99:
            return normalized
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12].upper()
        return f"{normalized[:86]}_{digest}"

    def _expand_table_names(
        self,
        table_names: tuple[str, ...] | None,
        *,
        relationship_expansion_depth: int,
        include_logical_relations_yn: str,
    ) -> tuple[str, ...] | None:
        """시작 Table에서 물리·논리 관계를 따라 지정 Depth까지 범위를 확장한다."""
        if not table_names:
            return table_names

        expansion_depth = int(relationship_expansion_depth)
        if expansion_depth < 0:
            raise ValueError(
                "relationship_expansion_depth must be zero or greater. "
                f"value={relationship_expansion_depth}"
            )
        if expansion_depth == 0:
            return table_names

        include_logical = (
            str(include_logical_relations_yn).strip().upper() == "Y"
        )
        adjacency: dict[str, set[str]] = {}

        for row in self._load_relationships(None):
            source_table = row["source_table"]
            target_table = row["target_table"]
            adjacency.setdefault(source_table, set()).add(target_table)
            adjacency.setdefault(target_table, set()).add(source_table)

        if include_logical:
            for related_tables in self._load_logical_relation_groups():
                for table_name in related_tables:
                    adjacency.setdefault(table_name, set()).update(
                        candidate
                        for candidate in related_tables
                        if candidate != table_name
                    )

        expanded = set(table_names)
        frontier = set(table_names)
        for _ in range(expansion_depth):
            next_frontier: set[str] = set()
            for table_name in frontier:
                next_frontier.update(adjacency.get(table_name, set()))
            next_frontier -= expanded
            if not next_frontier:
                break
            expanded.update(next_frontier)
            frontier = next_frontier

        return tuple(sorted(expanded))

    def _load_logical_relation_groups(self) -> list[tuple[str, ...]]:
        """PK/UK가 존재하는 공유 식별 컬럼별 논리 관계 Table 묶음을 조회한다."""
        rows = self.database.fetch_all(
            """
            SELECT
                column_name,
                GROUP_CONCAT(
                    DISTINCT table_name
                    ORDER BY table_name
                    SEPARATOR ','
                ) AS related_tables,
                SUM(CASE WHEN column_key IN ('PRI', 'UNI') THEN 1 ELSE 0 END) AS anchor_count,
                COUNT(DISTINCT table_name) AS table_count
            FROM information_schema.columns
            WHERE table_schema = %s
              AND RIGHT(column_name, 3) = '_id'
            GROUP BY column_name
            HAVING COUNT(DISTINCT table_name) >= 2
               AND SUM(CASE WHEN column_key IN ('PRI', 'UNI') THEN 1 ELSE 0 END) >= 1
            ORDER BY column_name
            """,
            (self.database.database_name,),
        )
        return [
            tuple(
                table_name
                for table_name in str(row["related_tables"]).split(",")
                if table_name
            )
            for row in rows
        ]

    @staticmethod
    def _normalize_table_names(
        table_names: Iterable[str] | None,
    ) -> tuple[str, ...] | None:
        if table_names is None:
            return None
        normalized = tuple(
            sorted({str(table_name).strip() for table_name in table_names if str(table_name).strip()})
        )
        return normalized or None

    @staticmethod
    def _build_table_filter(
        column_name: str,
        table_names: tuple[str, ...] | None,
    ) -> tuple[str, tuple[str, ...]]:
        if not table_names:
            return "", ()
        placeholders = ", ".join(["%s"] * len(table_names))
        return f"AND {column_name} IN ({placeholders})", table_names

    @staticmethod
    def _safe_mermaid_name(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]", "_", value)

    @staticmethod
    def _safe_mermaid_type(value: str) -> str:
        base_type = str(value).split("(", 1)[0].strip().upper()
        normalized = re.sub(r"[^A-Za-z0-9_]", "_", base_type)
        return normalized or "UNKNOWN"

    # Story : sp_metadata의 ERD 제외 Metadata를 공식 SSOT로 해석한다.
    def _load_metadata_excluded_columns(self) -> set[tuple[str, str]]:
        """COLUMN_NAME이 `[제외]name`이면 실제 `name`을 제외한다."""
        rows = self.repository_database.fetch_all(
            """
            SELECT source_story_text
            FROM sp_knowledge_hold
            WHERE active_yn = 'Y'
              AND deleted_yn = 'N'
              AND deleted_dt IS NULL
              AND source_story_text LIKE '%COLUMN_NAME:%[제외]%'
            """
        )
        excluded_columns: set[tuple[str, str]] = set()
        current_database_name = self.database.database_name.lower()

        for row in rows:
            story_text = str(row.get("source_story_text") or "")
            database_match = re.search(
                r"DATABASE_NAME\s*:\s*([A-Za-z0-9_]+)", story_text, re.IGNORECASE
            )
            table_match = re.search(
                r"TABLE_NAME\s*:\s*([A-Za-z0-9_]+)", story_text, re.IGNORECASE
            )
            column_match = re.search(
                r"COLUMN_NAME\s*:\s*\[제외\]\s*([A-Za-z0-9_]+)",
                story_text,
                re.IGNORECASE,
            )
            if database_match and database_match.group(1).lower() != current_database_name:
                continue
            if table_match and column_match:
                excluded_columns.add((table_match.group(1), column_match.group(1)))

        return excluded_columns

    def _load_table_scope_map(
        self,
        column_rows: list[dict[str, Any]],
    ) -> dict[str, tuple[str, str]]:
        """기존 sp_object Object ID와 PK Metadata로 업무 구역을 해석한다."""
        primary_key_by_table = {
            row["table_name"]: row["column_name"]
            for row in column_rows
            if row["column_key"] == "PRI"
        }

        object_rows = self.repository_database.fetch_all(
            """
            SELECT business_code, domain_code, target_identifier_field
            FROM sp_object
            WHERE object_type_code = 'TABLE'
              AND active_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
              AND target_identifier_field IS NOT NULL
            """
        )

        scope_by_primary_key = {
            row["target_identifier_field"]: (
                row["business_code"], row["domain_code"]
            )
            for row in object_rows
        }

        return {
            table_name: scope_by_primary_key.get(primary_key, ("ZZ", "ZZ"))
            for table_name, primary_key in primary_key_by_table.items()
        }

    @staticmethod
    def _order_tables_for_layout(
        table_rows: list[dict[str, Any]],
        relationship_rows: list[dict[str, Any]],
        table_scope_map: dict[str, tuple[str, str]],
    ) -> list[dict[str, Any]]:
        """관계가 많은 중심 Table부터 배치해 선 교차를 최소화한다."""
        relationship_count = {row["table_name"]: 0 for row in table_rows}
        for relationship in relationship_rows:
            source = relationship["source_table"]
            target = relationship["target_table"]
            if source in relationship_count:
                relationship_count[source] += 1
            if target in relationship_count:
                relationship_count[target] += 1

        return sorted(
            table_rows,
            key=lambda row: (
                table_scope_map.get(row["table_name"], ("ZZ", "ZZ")),
                -relationship_count[row["table_name"]],
                row["table_name"],
            ),
        )
