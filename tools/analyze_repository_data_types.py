"""SPS Repository Data Type Inventory Analyzer.

Reads column suffix standards from sp_metadata and compares every live column
across configured Repository database roles. This tool is read-only: it never
executes ALTER, INSERT, UPDATE, or DELETE.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase

DATABASE_ROLES = (
    "HEALTH_COMPANION",
    "STORY_PLATFORM",
    "COMMON",
)
METADATA_TYPE_CODE = "REQUIRED_SUFFIX_STANDARD"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "reports"
DEFAULT_BASENAME = "repository_data_type_inventory_20260719"

INTEGER_TYPES = {
    "tinyint",
    "smallint",
    "mediumint",
    "int",
    "integer",
    "bigint",
}
CHARACTER_TYPES = {
    "char",
    "varchar",
    "tinytext",
    "text",
    "mediumtext",
    "longtext",
}


def json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def normalize_sql_type(value: str) -> str:
    normalized = re.sub(r"\s+", "", str(value).strip().lower())
    normalized = normalized.replace("integer", "int")
    match = re.fullmatch(
        r"(tinyint|smallint|mediumint|int|bigint)\(\d+\)(unsigned)?",
        normalized,
    )
    if match:
        return match.group(1) + (match.group(2) or "")
    return normalized


def type_family(value: str) -> str:
    normalized = normalize_sql_type(value)
    base_type = normalized.split("(", 1)[0].replace("unsigned", "")
    if base_type in INTEGER_TYPES:
        return "INTEGER"
    if base_type in CHARACTER_TYPES:
        return "CHARACTER"
    if base_type in {"decimal", "numeric", "float", "double", "real"}:
        return "DECIMAL"
    if base_type in {"date", "time", "datetime", "timestamp"}:
        return "TEMPORAL"
    if base_type in {"binary", "varbinary", "blob", "tinyblob", "mediumblob", "longblob"}:
        return "BINARY"
    return base_type.upper()


def declared_character_length(value: str) -> int | None:
    match = re.fullmatch(
        r"(?:var)?char\((\d+)\)",
        normalize_sql_type(value),
    )
    return int(match.group(1)) if match else None


def resolve_database_names() -> dict[str, str]:
    result: dict[str, str] = {}
    for role in DATABASE_ROLES:
        database = CommonDatabase(database_role=role)
        try:
            result[role] = str(database.database_name)
        finally:
            database.close()
    return result


def resolve_metadata_target(database: CommonDatabase) -> str:
    row = database.fetch_one(
        """
        SELECT object_id
        FROM sp_object
        WHERE object_code = 'METADATA'
          AND deleted_dt IS NULL
        ORDER BY object_level DESC, created_dt
        LIMIT 1
        """
    )
    if not row:
        raise RuntimeError("Active METADATA Object was not found in sp_object.")
    return str(row["object_id"])


def load_suffix_standards() -> tuple[str, list[dict[str, Any]]]:
    database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        target_id = resolve_metadata_target(database)
        rows = database.fetch_all(
            """
            SELECT
                metadata_id,
                metadata_key,
                metadata_value,
                metadata_json,
                sort_no
            FROM sp_metadata
            WHERE target_type_code = 'COLUMN'
              AND target_id = %s
              AND metadata_type_code = %s
              AND enabled_yn = 'Y'
              AND deleted_dt IS NULL
            ORDER BY
                CHAR_LENGTH(metadata_key) DESC,
                sort_no,
                metadata_key
            """,
            (target_id, METADATA_TYPE_CODE),
        )
    finally:
        database.close()

    standards: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for row in rows or []:
        suffix = str(row["metadata_key"]).strip().lower()
        sql_type = str(row["metadata_value"]).strip().upper()
        if not suffix.startswith("_") or not sql_type:
            continue
        if suffix in seen_keys:
            raise RuntimeError(f"Duplicate suffix Metadata found: {suffix}")
        seen_keys.add(suffix)

        metadata_json: dict[str, Any] = {}
        if row.get("metadata_json"):
            try:
                metadata_json = json.loads(row["metadata_json"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    f"Invalid metadata_json for suffix {suffix}"
                ) from exc

        standards.append(
            {
                "metadata_id": row["metadata_id"],
                "suffix": suffix,
                "sql_type": sql_type,
                "normalized_sql_type": normalize_sql_type(sql_type),
                "metadata_json": metadata_json,
                "sort_no": row["sort_no"],
            }
        )

    if not standards:
        raise RuntimeError(
            "No active REQUIRED_SUFFIX_STANDARD rows were found in sp_metadata."
        )

    standards.sort(
        key=lambda item: (
            -len(item["suffix"]),
            int(item["sort_no"] or 0),
            item["suffix"],
        )
    )
    return target_id, standards


def load_columns(
    database_names: dict[str, str],
) -> list[dict[str, Any]]:
    names = [database_names[role] for role in DATABASE_ROLES]
    placeholders = ", ".join(["%s"] * len(names))
    database = CommonDatabase(database_role="COMMON")
    try:
        rows = database.fetch_all(
            f"""
            SELECT
                columns.table_schema,
                columns.table_name,
                tables.table_type,
                tables.table_rows,
                tables.table_comment,
                columns.ordinal_position,
                columns.column_name,
                columns.column_type,
                columns.data_type,
                columns.character_maximum_length,
                columns.numeric_precision,
                columns.numeric_scale,
                columns.is_nullable,
                columns.column_default,
                columns.extra,
                columns.column_key,
                columns.column_comment,
                columns.generation_expression
            FROM information_schema.columns columns
            JOIN information_schema.tables tables
              ON tables.table_schema = columns.table_schema
             AND tables.table_name = columns.table_name
            WHERE columns.table_schema IN ({placeholders})
            ORDER BY
                FIELD(columns.table_schema, {placeholders}),
                columns.table_name,
                columns.ordinal_position
            """,
            tuple(names + names),
        )
    finally:
        database.close()
    return [dict(row) for row in (rows or [])]


def load_foreign_keys(
    database_names: dict[str, str],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    names = [database_names[role] for role in DATABASE_ROLES]
    placeholders = ", ".join(["%s"] * len(names))
    database = CommonDatabase(database_role="COMMON")
    try:
        rows = database.fetch_all(
            f"""
            SELECT
                constraint_schema,
                table_name,
                column_name,
                constraint_name,
                referenced_table_schema,
                referenced_table_name,
                referenced_column_name
            FROM information_schema.key_column_usage
            WHERE constraint_schema IN ({placeholders})
              AND referenced_table_name IS NOT NULL
            ORDER BY
                constraint_schema,
                table_name,
                constraint_name,
                ordinal_position
            """,
            tuple(names),
        )
    finally:
        database.close()

    result: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows or []:
        item = dict(row)
        key = (
            str(item["constraint_schema"]),
            str(item["table_name"]),
            str(item["column_name"]),
        )
        result[key].append(item)

        referenced_key = (
            str(item["referenced_table_schema"]),
            str(item["referenced_table_name"]),
            str(item["referenced_column_name"]),
        )
        result[referenced_key].append(
            {
                **item,
                "relation_direction": "REFERENCED_BY",
            }
        )
    return result


def match_standard(
    column_name: str,
    standards: list[dict[str, Any]],
) -> dict[str, Any] | None:
    normalized_name = column_name.lower()
    for standard in standards:
        if normalized_name.endswith(standard["suffix"]):
            return standard
    return None


def assess_change(
    column: dict[str, Any],
    standard: dict[str, Any] | None,
    foreign_keys: list[dict[str, Any]],
) -> tuple[str, str, str]:
    if standard is None:
        return "NO_STANDARD", "NONE", "No suffix Metadata matched."

    actual = normalize_sql_type(column["column_type"])
    expected = standard["normalized_sql_type"]

    if actual == expected:
        return "COMPLIANT", "NONE", "Current type matches Metadata."

    if str(column["table_type"]).upper() == "VIEW":
        return (
            "VIEW_RECREATE_REQUIRED",
            "HIGH",
            "View column type follows its source expression.",
        )

    extra = str(column.get("extra") or "").lower()
    if "auto_increment" in extra:
        return (
            "MISMATCH",
            "CRITICAL",
            "AUTO_INCREMENT identifier requires a separate ID migration.",
        )

    if foreign_keys:
        return (
            "MISMATCH",
            "HIGH",
            "Foreign-key relation must be changed as one dependency group.",
        )

    current_length = column.get("character_maximum_length")
    target_length = declared_character_length(standard["sql_type"])
    if (
        current_length is not None
        and target_length is not None
        and int(current_length) > target_length
    ):
        return (
            "MISMATCH",
            "HIGH",
            "Target character length is smaller; data profiling is required.",
        )

    if type_family(actual) != type_family(expected):
        return (
            "MISMATCH",
            "HIGH",
            "Data type family changes; conversion profiling is required.",
        )

    return (
        "MISMATCH",
        "MEDIUM",
        "Schema change requires default, nullability, index, and comment preservation.",
    )


def analyze() -> dict[str, Any]:
    database_names = resolve_database_names()
    metadata_target_id, standards = load_suffix_standards()
    columns = load_columns(database_names)
    foreign_key_map = load_foreign_keys(database_names)
    role_by_database = {
        database_name: role
        for role, database_name in database_names.items()
    }

    results: list[dict[str, Any]] = []
    for column in columns:
        standard = match_standard(str(column["column_name"]), standards)
        key = (
            str(column["table_schema"]),
            str(column["table_name"]),
            str(column["column_name"]),
        )
        relations = foreign_key_map.get(key, [])
        status, risk, reason = assess_change(column, standard, relations)

        results.append(
            {
                **column,
                "database_role": role_by_database.get(
                    str(column["table_schema"])
                ),
                "matched_suffix": (
                    standard["suffix"] if standard else None
                ),
                "standard_metadata_id": (
                    standard["metadata_id"] if standard else None
                ),
                "expected_column_type": (
                    standard["sql_type"] if standard else None
                ),
                "normalized_current_type": normalize_sql_type(
                    str(column["column_type"])
                ),
                "normalized_expected_type": (
                    standard["normalized_sql_type"]
                    if standard
                    else None
                ),
                "assessment_status": status,
                "change_risk": risk,
                "assessment_reason": reason,
                "foreign_key_count": len(relations),
                "foreign_keys": relations,
            }
        )

    status_counts = Counter(
        item["assessment_status"] for item in results
    )
    risk_counts = Counter(item["change_risk"] for item in results)
    database_summary: dict[str, dict[str, int]] = {}

    for role in DATABASE_ROLES:
        role_rows = [
            item for item in results
            if item["database_role"] == role
        ]
        database_summary[role] = {
            "columns": len(role_rows),
            "compliant": sum(
                item["assessment_status"] == "COMPLIANT"
                for item in role_rows
            ),
            "mismatch": sum(
                item["assessment_status"] == "MISMATCH"
                for item in role_rows
            ),
            "view_recreate_required": sum(
                item["assessment_status"] == "VIEW_RECREATE_REQUIRED"
                for item in role_rows
            ),
            "no_standard": sum(
                item["assessment_status"] == "NO_STANDARD"
                for item in role_rows
            ),
        }

    return {
        "generated_dt": datetime.now().isoformat(timespec="seconds"),
        "read_only": True,
        "database_order": list(DATABASE_ROLES),
        "database_names": database_names,
        "metadata_target_id": metadata_target_id,
        "metadata_type_code": METADATA_TYPE_CODE,
        "standard_count": len(standards),
        "standards": standards,
        "summary": {
            "column_count": len(results),
            "status_counts": dict(sorted(status_counts.items())),
            "risk_counts": dict(sorted(risk_counts.items())),
            "database_summary": database_summary,
        },
        "columns": results,
    }


def write_json(path: Path, report: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            default=json_default,
        )
        + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, report: dict[str, Any]) -> None:
    field_names = (
        "database_role",
        "table_schema",
        "table_name",
        "table_type",
        "ordinal_position",
        "column_name",
        "column_type",
        "expected_column_type",
        "matched_suffix",
        "assessment_status",
        "change_risk",
        "foreign_key_count",
        "is_nullable",
        "column_default",
        "extra",
        "column_key",
        "assessment_reason",
    )
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=field_names)
        writer.writeheader()
        for item in report["columns"]:
            writer.writerow(
                {
                    field_name: item.get(field_name)
                    for field_name in field_names
                }
            )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare live Repository columns with sp_metadata suffix standards."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--basename",
        default=DEFAULT_BASENAME,
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    output_dir = arguments.output_dir.resolve()
    project_root = PROJECT_ROOT.resolve()

    if (
        output_dir != project_root
        and project_root not in output_dir.parents
    ):
        raise ValueError("output-dir must stay inside the project root.")
    output_dir.mkdir(parents=True, exist_ok=True)

    report = analyze()
    json_path = output_dir / f"{arguments.basename}.json"
    csv_path = output_dir / f"{arguments.basename}.csv"

    write_json(json_path, report)
    write_csv(csv_path, report)

    summary = report["summary"]
    print("=" * 80)
    print("SPS Repository Data Type Inventory SUCCESS")
    print("=" * 80)
    print(f"Metadata target : {report['metadata_target_id']}")
    print(f"Standards       : {report['standard_count']}")
    print(f"Columns         : {summary['column_count']}")
    print(f"JSON            : {json_path}")
    print(f"CSV             : {csv_path}")
    print("-" * 80)
    for role in DATABASE_ROLES:
        item = summary["database_summary"][role]
        print(
            f"{role:<20} "
            f"columns={item['columns']:<5} "
            f"compliant={item['compliant']:<5} "
            f"mismatch={item['mismatch']:<5} "
            f"view={item['view_recreate_required']:<5} "
            f"no_standard={item['no_standard']:<5}"
        )
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
