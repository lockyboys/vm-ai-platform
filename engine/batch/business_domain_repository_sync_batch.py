"""Synchronize physical database metadata into SPS repositories.

cm_business_domain is the SSOT for selectable business domain codes.
Only DML is performed; no database structure is created or altered.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from typing import Any, Iterable

from common.database import CommonDatabase
from engine.identifier_engine import IdentifierEngine


@dataclass(slots=True)
class SyncCounts:
    inserted: dict[str, int] = field(default_factory=dict)
    updated: dict[str, int] = field(default_factory=dict)
    skipped_tables: list[str] = field(default_factory=list)

    def add(self, bucket: str, created: bool) -> None:
        target = self.inserted if created else self.updated
        target[bucket] = target.get(bucket, 0) + 1


class BusinessDomainRepositorySyncBatch:
    """Idempotent Table → Entity → Attribute → ERD → Relationship batch."""

    PROGRAM_ID = "business_domain_repository_sync_batch.py"
    IDENTIFIER_OBJECT_CODES = {
        "table": "TABLE",
        "entity": "ENTITY",
        "attribute": "ATTRIBUTE",
        "erd": "ERD",
        "relationship": "RELATIONSHIP",
    }

    def __init__(
        self,
        source_database: CommonDatabase,
        *,
        business_code: str,
        common_database: CommonDatabase | None = None,
        repository_database: CommonDatabase | None = None,
        actor_id: str = "SYSTEM",
        client_ip: str = "127.0.0.1",
    ) -> None:
        self.source = source_database
        self.common = common_database or CommonDatabase(database_role="COMMON")
        self.repository = repository_database or CommonDatabase(
            database_role="STORY_PLATFORM"
        )
        self.business_code = business_code.strip().upper()
        self.actor_id = actor_id
        self.client_ip = client_ip
        self.identifier = IdentifierEngine(self.repository)

    def run(self, *, apply: bool = False) -> dict[str, Any]:
        domains = self._load_business_domains()
        self._validate_business()
        tables = self._load_tables(domains)
        columns = self._load_columns({row["table_name"] for row in tables})
        foreign_keys = self._load_foreign_keys({row["table_name"] for row in tables})
        required_identifier_buckets = self._required_identifier_buckets(
            tables=tables,
            columns=columns,
            foreign_keys=foreign_keys,
        )
        self._validate_identifier_metadata(required_identifier_buckets)

        plan = {
            "source_database_role": self.source.database_role,
            "source_database_name": self.source.database_name,
            "business_code": self.business_code,
            "domain_codes": sorted(domains),
            "table_count": len(tables),
            "column_count": len(columns),
            "foreign_key_count": len(foreign_keys),
            "required_identifier_object_codes": [
                self.IDENTIFIER_OBJECT_CODES[bucket]
                for bucket in required_identifier_buckets
            ],
            "apply": apply,
        }
        if not apply:
            return plan

        counts = SyncCounts()
        self.repository.begin()
        try:
            entity_by_table: dict[str, str] = {}
            erd_by_domain: dict[str, str] = {}
            for table in tables:
                self._sync_table_object(table, columns, counts)
                entity_id = self._sync_entity(table, counts)
                entity_by_table[table["table_name"]] = entity_id
                self._sync_attributes(entity_id, table["table_name"], columns, counts)
                domain_code = table["domain_code"]
                if domain_code not in erd_by_domain:
                    erd_by_domain[domain_code] = self._sync_erd(
                        domain_code, domains, counts
                    )

            for foreign_key in foreign_keys:
                source_entity_id = entity_by_table.get(foreign_key["source_table"])
                target_entity_id = entity_by_table.get(foreign_key["target_table"])
                if source_entity_id and target_entity_id:
                    domain_code = self._domain_code(foreign_key["source_table"], domains)
                    self._sync_fk_relationship(
                        foreign_key,
                        erd_by_domain[domain_code],
                        source_entity_id,
                        target_entity_id,
                        counts,
                    )
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

        plan["inserted"] = counts.inserted
        plan["updated"] = counts.updated
        plan["skipped_tables"] = counts.skipped_tables
        return plan

    def _load_business_domains(self) -> dict[str, dict[str, Any]]:
        rows = self.common.fetch_all(
            """
            SELECT business_domain_code, business_domain_name, description, sort_no
            FROM cm_business_domain
            WHERE status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY sort_no, business_domain_code
            """
        )
        if not rows:
            raise ValueError("Active cm_business_domain metadata not found.")
        return {str(row["business_domain_code"]).upper(): dict(row) for row in rows}

    def _validate_business(self) -> None:
        row = self.repository.fetch_one(
            """
            SELECT business_code
            FROM sp_business
            WHERE business_code = %s
              AND active_yn = 'Y'
              AND deleted_dt IS NULL
            """,
            (self.business_code,),
        )
        if not row:
            raise ValueError(
                "Active business metadata not found. "
                f"business_code={self.business_code}"
            )

    @staticmethod
    def _required_identifier_buckets(
        *,
        tables: list[dict[str, Any]],
        columns: list[dict[str, Any]],
        foreign_keys: list[dict[str, Any]],
    ) -> tuple[str, ...]:
        required = []
        if tables:
            required.extend(("table", "entity", "erd"))
        if columns:
            required.append("attribute")
        if foreign_keys:
            required.append("relationship")
        return tuple(required)

    def _validate_identifier_metadata(self, buckets: Iterable[str]) -> None:
        missing = []
        for bucket in buckets:
            object_code = self.IDENTIFIER_OBJECT_CODES[bucket]
            try:
                self.identifier.load_object_metadata(object_code)
            except ValueError:
                missing.append(object_code)
        if missing:
            raise ValueError(f"Identifier object metadata not found: {missing}")

    def _load_tables(
        self, domains: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rows = self.source.fetch_all(
            """
            SELECT table_name, table_comment
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            (self.source.database_name,),
        )
        result = []
        for row in rows:
            domain_code = self._domain_code(str(row["table_name"]), domains, strict=False)
            if domain_code:
                item = dict(row)
                item["domain_code"] = domain_code
                result.append(item)
        return result

    def _load_columns(self, table_names: set[str]) -> list[dict[str, Any]]:
        if not table_names:
            return []
        placeholders = ", ".join(["%s"] * len(table_names))
        return self.source.fetch_all(
            f"""
            SELECT table_name, column_name, data_type, character_maximum_length,
                   numeric_scale, is_nullable, column_key, column_default,
                   column_comment, ordinal_position
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name IN ({placeholders})
            ORDER BY table_name, ordinal_position
            """,
            (self.source.database_name, *sorted(table_names)),
        )

    def _load_foreign_keys(self, table_names: set[str]) -> list[dict[str, Any]]:
        if not table_names:
            return []
        placeholders = ", ".join(["%s"] * len(table_names))
        return self.source.fetch_all(
            f"""
            SELECT kcu.constraint_name,
                   kcu.table_name AS source_table,
                   kcu.column_name AS source_column,
                   kcu.referenced_table_name AS target_table,
                   kcu.referenced_column_name AS target_column,
                   rc.update_rule, rc.delete_rule
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.referential_constraints rc
              ON rc.constraint_schema = kcu.constraint_schema
             AND rc.constraint_name = kcu.constraint_name
            WHERE kcu.table_schema = %s
              AND kcu.referenced_table_name IS NOT NULL
              AND kcu.table_name IN ({placeholders})
              AND kcu.referenced_table_name IN ({placeholders})
            ORDER BY kcu.table_name, kcu.constraint_name, kcu.ordinal_position
            """,
            (
                self.source.database_name,
                *sorted(table_names),
                *sorted(table_names),
            ),
        )

    @staticmethod
    def _domain_code(
        table_name: str,
        domains: dict[str, dict[str, Any]],
        *,
        strict: bool = True,
    ) -> str | None:
        prefix = table_name.split("_", 1)[0].upper()
        if prefix in domains:
            return prefix
        if strict:
            raise ValueError(
                f"Table prefix is not registered in cm_business_domain: {table_name}"
            )
        return None

    def _generate_id(self, bucket: str) -> str:
        return self.identifier.generate(
            self.IDENTIFIER_OBJECT_CODES[bucket],
            manage_transaction=False,
        )

    def _sync_table_object(
        self,
        table: dict[str, Any],
        columns: list[dict[str, Any]],
        counts: SyncCounts,
    ) -> str:
        object_code = (
            f"{self.source.database_name}_{table['table_name']}".upper()
        )
        primary_keys = [
            row["column_name"]
            for row in columns
            if row["table_name"] == table["table_name"] and row["column_key"] == "PRI"
        ]
        target_field = primary_keys[0] if len(primary_keys) == 1 else None
        existing = self.repository.fetch_one(
            "SELECT object_id FROM sp_object WHERE object_code = %s",
            (object_code,),
        )
        created = not bool(existing)
        object_id = (
            str(existing["object_id"]) if existing else self._generate_id("table")
        )
        self.repository.execute(
            """
            INSERT INTO sp_object
            (object_id, object_code, object_name, business_code, domain_code,
             object_type_code, object_description, object_level, status_code,
             active_yn, target_identifier_field, created_by, updated_by,
             client_ip, program_id)
            VALUES
            (%s, %s, %s, %s, %s, 'TABLE', %s, 3, 'ACTIVE', 'Y', %s,
             %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                object_name = VALUES(object_name),
                business_code = VALUES(business_code),
                domain_code = VALUES(domain_code),
                object_description = VALUES(object_description),
                status_code = 'ACTIVE',
                active_yn = 'Y',
                target_identifier_field = VALUES(target_identifier_field),
                deleted_by = NULL,
                deleted_dt = NULL,
                updated_by = VALUES(updated_by),
                client_ip = VALUES(client_ip),
                program_id = VALUES(program_id)
            """,
            (
                object_id,
                object_code,
                f"{self.source.database_name}.{table['table_name']}",
                self.business_code,
                table["domain_code"],
                table.get("table_comment") or None,
                target_field,
                self.actor_id,
                self.actor_id,
                self.client_ip,
                self.PROGRAM_ID,
            ),
        )
        counts.add("table", created)
        return object_id

    def _sync_entity(self, table: dict[str, Any], counts: SyncCounts) -> str:
        entity_name = f"{self.source.database_name}.{table['table_name']}"
        existing = self.repository.fetch_one(
            "SELECT entity_id FROM sp_entity WHERE entity_name = %s",
            (entity_name,),
        )
        created = not bool(existing)
        entity_id = (
            str(existing["entity_id"]) if existing else self._generate_id("entity")
        )
        self.repository.execute(
            """
            INSERT INTO sp_entity
            (entity_id, entity_name, business_code, domain_code, entity_comment,
             entity_type_code, enabled_yn, created_by, updated_by, client_ip, program_id)
            VALUES (%s, %s, %s, %s, %s, 'MASTER', 'Y', %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                business_code = VALUES(business_code),
                domain_code = VALUES(domain_code),
                entity_comment = VALUES(entity_comment),
                enabled_yn = 'Y',
                deleted_by = NULL,
                deleted_dt = NULL,
                updated_by = VALUES(updated_by),
                client_ip = VALUES(client_ip),
                program_id = VALUES(program_id)
            """,
            (
                entity_id,
                entity_name,
                self.business_code,
                table["domain_code"],
                table.get("table_comment") or None,
                self.actor_id,
                self.actor_id,
                self.client_ip,
                self.PROGRAM_ID,
            ),
        )
        counts.add("entity", created)
        return entity_id

    def _sync_attributes(
        self,
        entity_id: str,
        table_name: str,
        columns: list[dict[str, Any]],
        counts: SyncCounts,
    ) -> None:
        for column in (row for row in columns if row["table_name"] == table_name):
            existing = self.repository.fetch_one(
                """
                SELECT attribute_id
                FROM sp_attribute
                WHERE entity_id = %s AND attribute_name = %s
                """,
                (entity_id, column["column_name"]),
            )
            created = not bool(existing)
            attribute_id = (
                str(existing["attribute_id"])
                if existing
                else self._generate_id("attribute")
            )
            self.repository.execute(
                """
                INSERT INTO sp_attribute
                (attribute_id, entity_id, attribute_name, data_type, length_no,
                 scale_no, nullable_yn, primary_key_yn, unique_yn, default_value,
                 attribute_comment, sort_no, created_by, updated_by, client_ip, program_id)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                 %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    data_type = VALUES(data_type),
                    length_no = VALUES(length_no),
                    scale_no = VALUES(scale_no),
                    nullable_yn = VALUES(nullable_yn),
                    primary_key_yn = VALUES(primary_key_yn),
                    unique_yn = VALUES(unique_yn),
                    default_value = VALUES(default_value),
                    attribute_comment = VALUES(attribute_comment),
                    sort_no = VALUES(sort_no),
                    deleted_by = NULL,
                    deleted_dt = NULL,
                    updated_by = VALUES(updated_by),
                    client_ip = VALUES(client_ip),
                    program_id = VALUES(program_id)
                """,
                (
                    attribute_id,
                    entity_id,
                    column["column_name"],
                    str(column["data_type"]).upper(),
                    column.get("character_maximum_length"),
                    column.get("numeric_scale"),
                    "Y" if column["is_nullable"] == "YES" else "N",
                    "Y" if column["column_key"] == "PRI" else "N",
                    "Y" if column["column_key"] == "UNI" else "N",
                    column.get("column_default"),
                    column.get("column_comment") or None,
                    column["ordinal_position"],
                    self.actor_id,
                    self.actor_id,
                    self.client_ip,
                    self.PROGRAM_ID,
                ),
            )
            counts.add("attribute", created)

    def _sync_erd(
        self,
        domain_code: str,
        domains: dict[str, dict[str, Any]],
        counts: SyncCounts,
    ) -> str:
        erd_code = (
            f"{self.source.database_name}_{self.business_code}_{domain_code}_ERD"
        ).upper()
        existing = self.repository.fetch_one(
            "SELECT erd_id FROM sp_erd WHERE erd_code = %s",
            (erd_code,),
        )
        created = not bool(existing)
        erd_id = str(existing["erd_id"]) if existing else self._generate_id("erd")
        metadata = domains[domain_code]
        self.repository.execute(
            """
            INSERT INTO sp_erd
            (erd_id, erd_code, erd_name, business_code, domain_code,
             erd_description, enabled_yn, sort_no, created_by, updated_by,
             client_ip, program_id)
            VALUES (%s, %s, %s, %s, %s, %s, 'Y', %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                erd_name = VALUES(erd_name),
                business_code = VALUES(business_code),
                domain_code = VALUES(domain_code),
                erd_description = VALUES(erd_description),
                enabled_yn = 'Y',
                sort_no = VALUES(sort_no),
                deleted_by = NULL,
                deleted_dt = NULL,
                updated_by = VALUES(updated_by),
                client_ip = VALUES(client_ip),
                program_id = VALUES(program_id)
            """,
            (
                erd_id,
                erd_code,
                f"{metadata['business_domain_name']} ERD",
                self.business_code,
                domain_code,
                metadata.get("description") or None,
                metadata.get("sort_no") or 0,
                self.actor_id,
                self.actor_id,
                self.client_ip,
                self.PROGRAM_ID,
            ),
        )
        counts.add("erd", created)
        return erd_id

    def _sync_fk_relationship(
        self,
        foreign_key: dict[str, Any],
        erd_id: str,
        source_entity_id: str,
        target_entity_id: str,
        counts: SyncCounts,
    ) -> None:
        code = (
            f"FK_{self.source.database_name}_{foreign_key['constraint_name']}"
        ).upper()
        self._upsert_relationship(
            code=code,
            name=str(foreign_key["constraint_name"]),
            description=(
                f"{foreign_key['source_table']}.{foreign_key['source_column']} -> "
                f"{foreign_key['target_table']}.{foreign_key['target_column']}"
            ),
            erd_id=erd_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            source_object_id=None,
            target_object_id=None,
            relationship_type_code="FK",
            delete_rule_code=foreign_key.get("delete_rule"),
            update_rule_code=foreign_key.get("update_rule"),
            counts=counts,
        )

    def _upsert_relationship(
        self,
        *,
        code: str,
        name: str,
        description: str,
        erd_id: str,
        source_entity_id: str,
        target_entity_id: str,
        source_object_id: str | None,
        target_object_id: str | None,
        relationship_type_code: str,
        delete_rule_code: str | None,
        update_rule_code: str | None,
        counts: SyncCounts,
    ) -> None:
        existing = self.repository.fetch_one(
            "SELECT relationship_id FROM sp_relationship WHERE relationship_code = %s",
            (code,),
        )
        created = not bool(existing)
        relationship_id = (
            str(existing["relationship_id"])
            if existing
            else self._generate_id("relationship")
        )
        self.repository.execute(
            """
            INSERT INTO sp_relationship
            (relationship_id, relationship_scope_code, erd_id,
             source_entity_id, target_entity_id, relationship_code,
             relationship_name, relationship_description, relationship_type_code,
             delete_rule_code, update_rule_code, enabled_yn, created_by, updated_by,
             client_ip, program_id)
            VALUES
            (%s, 'ERD', %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Y',
             %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                erd_id = VALUES(erd_id),
                source_entity_id = VALUES(source_entity_id),
                target_entity_id = VALUES(target_entity_id),
                relationship_name = VALUES(relationship_name),
                relationship_description = VALUES(relationship_description),
                relationship_type_code = VALUES(relationship_type_code),
                delete_rule_code = VALUES(delete_rule_code),
                update_rule_code = VALUES(update_rule_code),
                enabled_yn = 'Y',
                deleted_by = NULL,
                deleted_dt = NULL,
                updated_by = VALUES(updated_by),
                client_ip = VALUES(client_ip),
                program_id = VALUES(program_id)
            """,
            (
                relationship_id,
                erd_id,
                source_entity_id,
                target_entity_id,
                code,
                name,
                description,
                relationship_type_code,
                delete_rule_code,
                update_rule_code,
                self.actor_id,
                self.actor_id,
                self.client_ip,
                self.PROGRAM_ID,
            ),
        )
        counts.add("relationship", created)


def _parse_target(value: str) -> tuple[str, str]:
    role, separator, business_code = value.partition(":")
    if not separator or not role.strip() or not business_code.strip():
        raise argparse.ArgumentTypeError("target must be DATABASE_ROLE:BUSINESS_CODE")
    return role.strip().upper(), business_code.strip().upper()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        action="append",
        required=True,
        type=_parse_target,
        help="Repeatable DATABASE_ROLE:BUSINESS_CODE target.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply repository DML. Without this flag the batch is read-only.",
    )
    arguments = parser.parse_args(list(argv) if argv is not None else None)

    results = []
    common = CommonDatabase(database_role="COMMON")
    repository = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        for database_role, business_code in arguments.target:
            source = CommonDatabase(database_role=database_role)
            try:
                batch = BusinessDomainRepositorySyncBatch(
                    source,
                    business_code=business_code,
                    common_database=common,
                    repository_database=repository,
                )
                results.append(batch.run(apply=arguments.apply))
            finally:
                source.close()
    finally:
        repository.close()
        common.close()

    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
