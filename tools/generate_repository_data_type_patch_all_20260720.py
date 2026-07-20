# =============================================================================
# File Name : tools/generate_repository_data_type_patch_all_20260720.py
# Purpose   : Generate one hardcoded SQL patch for all live Data Type mismatches
# =============================================================================

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase


SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/reports/repository_data_type_inventory_20260719_mismatch.csv"
)
OUTPUT_SQL = (
    PROJECT_ROOT
    / "sql/runtime/repository_data_type_patch_all_20260720.sql"
)
HOLD_CSV = (
    PROJECT_ROOT
    / "outputs/reports/repository_data_type_patch_all_20260720_hold.csv"
)
DATABASE_ROLE = "COMMON"
BACKUP_SUFFIX = "_backup_20260720_01"

DATABASE_ORDER = {
    "te_health_companion": 1,
    "te_story_platform": 2,
    "te_common": 3,
}


def q(identifier: str) -> str:
    return "`" + identifier.replace("`", "``") + "`"


def sql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def normalized(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def table_exists(database: CommonDatabase, schema: str, table: str) -> bool:
    row = database.fetch_one(
        """
        SELECT COUNT(*) AS table_count
        FROM information_schema.tables
        WHERE table_schema=%s
          AND table_name=%s
          AND table_type='BASE TABLE'
        """,
        (schema, table),
    )
    return int(row["table_count"]) == 1


def live_column(
    database: CommonDatabase,
    schema: str,
    table: str,
    column: str,
):
    return database.fetch_one(
        """
        SELECT
            column_name,
            column_type,
            is_nullable,
            column_default,
            extra,
            column_comment,
            character_set_name,
            collation_name
        FROM information_schema.columns
        WHERE table_schema=%s
          AND table_name=%s
          AND column_name=%s
        """,
        (schema, table, column),
    )


def row_count(database: CommonDatabase, schema: str, table: str) -> int:
    row = database.fetch_one(
        f"SELECT COUNT(*) AS row_count FROM {q(schema)}.{q(table)}"
    )
    return int(row["row_count"])


def max_length(
    database: CommonDatabase,
    schema: str,
    table: str,
    column: str,
) -> int:
    row = database.fetch_one(
        f"""
        SELECT COALESCE(MAX(CHAR_LENGTH({q(column)})), 0) AS max_length
        FROM {q(schema)}.{q(table)}
        """
    )
    return int(row["max_length"])


def invalid_integer_count(
    database: CommonDatabase,
    schema: str,
    table: str,
    column: str,
) -> int:
    row = database.fetch_one(
        f"""
        SELECT COUNT(*) AS invalid_count
        FROM {q(schema)}.{q(table)}
        WHERE {q(column)} IS NOT NULL
          AND CAST({q(column)} AS CHAR) NOT REGEXP '^-?[0-9]+$'
        """
    )
    return int(row["invalid_count"])


def varchar_length(sql_type: str) -> int | None:
    match = re.fullmatch(r"varchar\((\d+)\)", normalized(sql_type))
    return int(match.group(1)) if match else None


def target_is_integer(sql_type: str) -> bool:
    return normalized(sql_type) in {
        "tinyint", "smallint", "mediumint", "int", "integer", "bigint"
    }


def conversion_is_safe(
    database: CommonDatabase,
    schema: str,
    table: str,
    column: str,
    actual_type: str,
    target_type: str,
    column_default,
    extra: str,
) -> tuple[bool, str]:
    if "auto_increment" in str(extra or "").lower():
        return False, "AUTO_INCREMENT_MIGRATION_REQUIRED"

    target_length = varchar_length(target_type)
    if target_length is not None:
        actual_max = max_length(database, schema, table, column)
        if actual_max > target_length:
            return False, f"MAX_LENGTH_{actual_max}_EXCEEDS_{target_length}"

    if target_is_integer(target_type):
        if invalid_integer_count(database, schema, table, column) > 0:
            return False, "NON_INTEGER_DATA"
        if column_default is not None and not re.fullmatch(
            r"-?[0-9]+", str(column_default)
        ):
            return False, "NON_INTEGER_DEFAULT"

    return True, "PASS"


def default_clause(column_default, is_nullable: str, target_type: str) -> str:
    if column_default is None:
        return " DEFAULT NULL" if is_nullable == "YES" else ""

    value = str(column_default)
    if value.upper() == "NULL":
        return " DEFAULT NULL"

    if re.fullmatch(
        r"(?i)(current_timestamp(?:\(\))?|current_date(?:\(\))?|current_time(?:\(\))?)",
        value,
    ):
        return f" DEFAULT {value}"

    if re.match(r"(?i)^(tinyint|smallint|mediumint|int|integer|bigint|decimal|numeric|float|double)", normalized(target_type)):
        if re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", value):
            return f" DEFAULT {value}"

    return " DEFAULT " + sql_string(value)


def modify_clause(column: dict, target_type: str) -> str:
    parts = [
        "MODIFY COLUMN",
        q(str(column["column_name"])),
        target_type.upper(),
        "NULL" if column["is_nullable"] == "YES" else "NOT NULL",
    ]
    definition = " ".join(parts)
    definition += default_clause(
        column["column_default"],
        str(column["is_nullable"]),
        target_type,
    )

    extra = str(column.get("extra") or "").strip()
    if extra:
        definition += " " + extra.upper()

    comment = str(column.get("column_comment") or "")
    if comment:
        definition += " COMMENT " + sql_string(comment)

    return definition


def main() -> None:
    with SOURCE_CSV.open("r", encoding="utf-8-sig", newline="") as file:
        source_rows = list(csv.DictReader(file))

    database = CommonDatabase(database_role=DATABASE_ROLE)
    holds: list[dict[str, str]] = []
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)

    try:
        for source in source_rows:
            schema = source["table_schema"]
            table = source["table_name"]
            column = source["column_name"]
            target_type = source["expected_column_type"]

            if "_backup_" in table:
                continue
            if not table_exists(database, schema, table):
                continue

            live = live_column(database, schema, table, column)
            if not live:
                continue
            if normalized(live["column_type"]) == normalized(target_type):
                continue

            safe, reason = conversion_is_safe(
                database,
                schema,
                table,
                column,
                str(live["column_type"]),
                target_type,
                live["column_default"],
                str(live["extra"] or ""),
            )
            if not safe:
                holds.append(
                    {
                        "table_schema": schema,
                        "table_name": table,
                        "column_name": column,
                        "actual_type": str(live["column_type"]),
                        "target_type": target_type,
                        "hold_reason": reason,
                    }
                )
                continue

            live["target_type"] = target_type
            groups[(schema, table)].append(live)

        ordered_groups = sorted(
            groups.items(),
            key=lambda item: (
                DATABASE_ORDER.get(item[0][0], 99),
                item[0][1],
            ),
        )

        lines = [
            "/*",
            "File Name : repository_data_type_patch_all_20260720.sql",
            "Purpose   : One-time hardcoded full Repository Data Type Patch.",
            f"Tables    : {len(ordered_groups)}",
            f"Columns   : {sum(len(columns) for _, columns in ordered_groups)}",
            f"HOLD      : {len(holds)} unsafe columns",
            "*/",
            "",
            "SET NAMES utf8mb4;",
            "SET FOREIGN_KEY_CHECKS = 0;",
            "",
        ]

        for patch_no, ((schema, table), columns) in enumerate(
            ordered_groups, start=1
        ):
            backup = table + BACKUP_SUFFIX
            count = row_count(database, schema, table)
            lines.extend(
                [
                    "/* =============================================================",
                    f"PATCH {patch_no:03d} START",
                    f"Database : {schema}",
                    f"Table    : {table}",
                    f"Columns  : {len(columns)}",
                    f"Rows     : {count}",
                    f"Backup   : {backup}",
                    "============================================================= */",
                    "",
                    "-- 1. 변경 전 백업",
                    f"CREATE TABLE {q(schema)}.{q(backup)}",
                    f"LIKE {q(schema)}.{q(table)};",
                    "",
                    "START TRANSACTION;",
                    "",
                    f"INSERT INTO {q(schema)}.{q(backup)}",
                    "SELECT *",
                    f"FROM {q(schema)}.{q(table)};",
                    "",
                    "COMMIT;",
                    "",
                    "-- 2. 백업 검증",
                    "SELECT",
                    f"    (SELECT COUNT(*) FROM {q(schema)}.{q(table)}) AS original_count,",
                    f"    (SELECT COUNT(*) FROM {q(schema)}.{q(backup)}) AS backup_count;",
                    "",
                    "-- 3. ALTER TABLE 문 실행",
                    f"ALTER TABLE {q(schema)}.{q(table)}",
                ]
            )
            clauses = [
                "    " + modify_clause(column, str(column["target_type"]))
                for column in columns
            ]
            lines.append(",\n".join(clauses) + ";")
            lines.extend(
                [
                    "",
                    "-- 4. 변경 결과 확인",
                    "SELECT column_name, column_type",
                    "FROM information_schema.columns",
                    f"WHERE table_schema = {sql_string(schema)}",
                    f"  AND table_name = {sql_string(table)}",
                    "  AND column_name IN (",
                    "      "
                    + ",\n      ".join(
                        sql_string(str(column["column_name"]))
                        for column in columns
                    ),
                    "  )",
                    "ORDER BY ordinal_position;",
                    "",
                    f"SELECT COUNT(*) AS row_count FROM {q(schema)}.{q(table)};",
                    "",
                    f"/* PATCH {patch_no:03d} END */",
                    "",
                ]
            )

        lines.extend(["SET FOREIGN_KEY_CHECKS = 1;", ""])
        OUTPUT_SQL.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_SQL.write_text("\n".join(lines), encoding="utf-8")

        HOLD_CSV.parent.mkdir(parents=True, exist_ok=True)
        with HOLD_CSV.open("w", encoding="utf-8-sig", newline="") as file:
            fieldnames = [
                "table_schema",
                "table_name",
                "column_name",
                "actual_type",
                "target_type",
                "hold_reason",
            ]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(holds)

        print(f"OUTPUT_SQL={OUTPUT_SQL.relative_to(PROJECT_ROOT)}")
        print(f"PATCH_TABLES={len(ordered_groups)}")
        print(f"PATCH_COLUMNS={sum(len(c) for _, c in ordered_groups)}")
        print(f"HOLD_COLUMNS={len(holds)}")
        print(f"HOLD_CSV={HOLD_CSV.relative_to(PROJECT_ROOT)}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
