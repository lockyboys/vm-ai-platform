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


def foreign_keys(database: CommonDatabase) -> list[dict]:
    """Load complete FK definitions so affected constraints can be rebuilt."""
    rows = database.fetch_all(
        """
        SELECT
            k.constraint_schema,
            k.table_name,
            k.constraint_name,
            k.column_name,
            k.referenced_table_schema,
            k.referenced_table_name,
            k.referenced_column_name,
            k.ordinal_position,
            r.update_rule,
            r.delete_rule
        FROM information_schema.key_column_usage k
        JOIN information_schema.referential_constraints r
          ON r.constraint_schema = k.constraint_schema
         AND r.table_name = k.table_name
         AND r.constraint_name = k.constraint_name
        WHERE k.referenced_table_name IS NOT NULL
          AND k.constraint_schema IN (%s, %s, %s)
        ORDER BY
            k.constraint_schema,
            k.table_name,
            k.constraint_name,
            k.ordinal_position
        """,
        tuple(DATABASE_ORDER),
    )
    grouped: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        key = (
            str(row["constraint_schema"]),
            str(row["table_name"]),
            str(row["constraint_name"]),
        )
        fk = grouped.setdefault(
            key,
            {
                "schema": key[0],
                "table": key[1],
                "name": key[2],
                "referenced_schema": str(row["referenced_table_schema"]),
                "referenced_table": str(row["referenced_table_name"]),
                "columns": [],
                "referenced_columns": [],
                "update_rule": str(row["update_rule"]),
                "delete_rule": str(row["delete_rule"]),
            },
        )
        fk["columns"].append(str(row["column_name"]))
        fk["referenced_columns"].append(str(row["referenced_column_name"]))
    return list(grouped.values())


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
    if (
        "auto_increment" in str(extra or "").lower()
        and varchar_length(target_type) is None
    ):
        return False, "AUTO_INCREMENT_MIGRATION_REQUIRED"

    target_length = varchar_length(target_type)
    if target_length is not None:
        actual_max = max_length(database, schema, table, column)
        if actual_max > target_length:
            return False, f"MAX_LENGTH_{actual_max}_EXCEEDS_{target_length}"

        index_row = database.fetch_one(
            """
            SELECT COUNT(*) AS index_count
            FROM information_schema.statistics
            WHERE table_schema=%s
              AND table_name=%s
              AND column_name=%s
            """,
            (schema, table, column),
        )
        if int(index_row["index_count"]) > 0 and target_length * 4 > 3072:
            return False, "INDEX_KEY_TOO_LONG"

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
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1].replace("''", "'").replace('""', '"')

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
    if "auto_increment" in extra.lower() and varchar_length(target_type) is not None:
        extra = re.sub(r"(?i)(^|\s)auto_increment(?=\s|$)", " ", extra).strip()
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

        patched_columns = {
            (schema, table, str(column["column_name"]))
            for (schema, table), columns in ordered_groups
            for column in columns
        }
        affected_foreign_keys = []
        for fk in foreign_keys(database):
            child_touches = any(
                (fk["schema"], fk["table"], column) in patched_columns
                for column in fk["columns"]
            )
            parent_touches = any(
                (
                    fk["referenced_schema"],
                    fk["referenced_table"],
                    column,
                ) in patched_columns
                for column in fk["referenced_columns"]
            )
            if child_touches or parent_touches:
                affected_foreign_keys.append(fk)

        lines = [
            "/*",
            "File Name : repository_data_type_patch_all_20260720.sql",
            "Purpose   : One-time hardcoded full Repository Data Type Patch.",
            f"Tables    : {len(ordered_groups)}",
            f"Columns   : {sum(len(columns) for _, columns in ordered_groups)}",
            f"HOLD      : {len(holds)} unsafe columns",
            f"FK Rebuild: {len(affected_foreign_keys)} constraints",
            "*/",
            "",
            "SET NAMES utf8mb4;",
            "SET FOREIGN_KEY_CHECKS = 0;",
            "",
        ]

        if affected_foreign_keys:
            lines.extend(
                [
                    "/* Affected foreign keys: drop before column migration */",
                    *[
                        f"ALTER TABLE {q(fk['schema'])}.{q(fk['table'])} "
                        f"DROP FOREIGN KEY {q(fk['name'])};"
                        for fk in affected_foreign_keys
                    ],
                    "",
                ]
            )

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
                ]
            )
            if table_exists(database, schema, backup):
                lines.extend(
                    [
                        "-- 1. 기존 백업 재사용",
                        "-- CREATE/INSERT 생략",
                        "",
                    ]
                )
            else:
                lines.extend(
                    [
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
                    ]
                )
            lines.extend(
                [
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

        if affected_foreign_keys:
            lines.extend(
                [
                    "/* Restore affected foreign keys with their original definitions */",
                    *[
                        f"ALTER TABLE {q(fk['schema'])}.{q(fk['table'])} "
                        f"ADD CONSTRAINT {q(fk['name'])} FOREIGN KEY ("
                        + ", ".join(q(column) for column in fk["columns"])
                        + f") REFERENCES {q(fk['referenced_schema'])}."
                        f"{q(fk['referenced_table'])} ("
                        + ", ".join(
                            q(column) for column in fk["referenced_columns"]
                        )
                        + f") ON UPDATE {fk['update_rule']}"
                        f" ON DELETE {fk['delete_rule']};"
                        for fk in affected_foreign_keys
                    ],
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
