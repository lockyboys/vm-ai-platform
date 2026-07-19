"""SPS Repository Data Type Inventory Analyzer.

Reads exact-name, compound-suffix, suffix, prefix, and root-token rules from
sp_metadata and compares every live column across configured Repository database
roles. This tool is read-only: it never executes ALTER, INSERT, UPDATE, or DELETE.
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
BASE_METADATA_TYPE_CODE = "REQUIRED_SUFFIX_STANDARD"
SUPPORTED_METADATA_CATEGORIES = {
    "COLUMN_SUFFIX_STANDARD",
    "COLUMN_NAMING_AND_DATA_TYPE_STANDARD",
    "COLUMN_VARCHAR_LENGTH_STANDARD",
}
MATCH_TYPE_RANK = {
    "EXACT": 5,
    "COMPOUND_SUFFIX": 4,
    "SUFFIX": 3,
    "PREFIX": 2,
    "ROOT": 1,
    "VARCHAR_LENGTH_BUCKET": 0,
}
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


def load_column_rules() -> tuple[str, list[dict[str, Any]]]:
    database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        target_id = resolve_metadata_target(database)
        rows = database.fetch_all(
            """
            SELECT
                metadata_id,
                metadata_type_code,
                metadata_key,
                metadata_value,
                metadata_json,
                sort_no
            FROM sp_metadata
            WHERE target_type_code = 'COLUMN'
              AND target_id = %s
              AND enabled_yn = 'Y'
              AND deleted_dt IS NULL
            ORDER BY
                sort_no,
                metadata_key
            """,
            (target_id,),
        )
    finally:
        database.close()

    rules: list[dict[str, Any]] = []
    seen_rules: set[tuple[str, str]] = set()

    for row in rows or []:
        metadata_json: dict[str, Any] = {}
        if row.get("metadata_json"):
            try:
                metadata_json = json.loads(row["metadata_json"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    f"Invalid metadata_json for {row['metadata_key']}"
                ) from exc

        metadata_type = str(row["metadata_type_code"]).strip().upper()
        category = str(metadata_json.get("category") or "").strip().upper()
        is_base_suffix = metadata_type == BASE_METADATA_TYPE_CODE
        if (
            not is_base_suffix
            and category not in SUPPORTED_METADATA_CATEGORIES
        ):
            continue

        match_type = str(
            metadata_json.get("match_type")
            or ("SUFFIX" if is_base_suffix else "")
        ).strip().upper()
        match_key = str(
            metadata_json.get("match_key")
            or metadata_json.get("suffix")
            or row["metadata_key"]
        ).strip().lower()
        if match_type not in MATCH_TYPE_RANK or not match_key:
            continue
        if (
            match_type in {"SUFFIX", "COMPOUND_SUFFIX"}
            and not match_key.startswith("_")
        ):
            raise RuntimeError(
                f"{match_type} Metadata must start with _: {match_key}"
            )

        identity = (match_type, match_key)
        if identity in seen_rules:
            raise RuntimeError(
                f"Duplicate column matching Metadata found: {identity}"
            )
        seen_rules.add(identity)

        raw_sql_type = (
            metadata_json.get("sql_type")
            or (row.get("metadata_value") if is_base_suffix else None)
        )
        sql_type = (
            str(raw_sql_type).strip().upper()
            if raw_sql_type is not None and str(raw_sql_type).strip()
            else None
        )
        priority = int(
            metadata_json.get("priority")
            or (600 if is_base_suffix else 0)
        )

        rules.append(
            {
                "metadata_id": row["metadata_id"],
                "metadata_type_code": metadata_type,
                "metadata_key": row["metadata_key"],
                "match_type": match_type,
                "match_key": match_key,
                "sql_type": sql_type,
                "normalized_sql_type": (
                    normalize_sql_type(sql_type) if sql_type else None
                ),
                "semantic_role": metadata_json.get("semantic_role"),
                "priority": priority,
                "rename_to": metadata_json.get("rename_to"),
                "rename_suffix": metadata_json.get("rename_suffix"),
                "metadata_json": metadata_json,
                "sort_no": row["sort_no"],
            }
        )

    if not any(rule["sql_type"] for rule in rules):
        raise RuntimeError(
            "No active column data type standard rows were found in sp_metadata."
        )

    rules.sort(
        key=lambda item: (
            -MATCH_TYPE_RANK[item["match_type"]],
            -int(item["priority"]),
            -len(item["match_key"]),
            int(item["sort_no"] or 0),
            item["match_key"],
        )
    )
    return target_id, rules


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


def rule_matches(column_name: str, rule: dict[str, Any]) -> bool:
    normalized_name = column_name.lower()
    match_type = rule["match_type"]
    match_key = rule["match_key"]
    if match_type == "EXACT":
        return normalized_name == match_key
    if match_type in {"COMPOUND_SUFFIX", "SUFFIX"}:
        return normalized_name.endswith(match_key)
    if match_type == "PREFIX":
        return normalized_name.startswith(match_key)
    if match_type == "ROOT":
        return match_key in normalized_name.split("_")
    return False


def match_varchar_length_standard(
    column: dict[str, Any],
    rules: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if str(column.get("data_type") or "").strip().lower() != "varchar":
        return None
    raw_length = column.get("character_maximum_length")
    if raw_length is None:
        return None
    current_length = int(raw_length)
    for rule in rules:
        if rule["match_type"] != "VARCHAR_LENGTH_BUCKET":
            continue
        metadata_json = rule["metadata_json"]
        minimum_length = int(metadata_json["minimum_length"])
        maximum_length = int(metadata_json["maximum_length"])
        if minimum_length <= current_length <= maximum_length:
            return rule
    return None


def find_matching_rules(
    column_name: str,
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [rule for rule in rules if rule_matches(column_name, rule)]


def match_type_standard(
    matching_rules: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return next(
        (rule for rule in matching_rules if rule["sql_type"]),
        None,
    )


def recommended_column_name(
    column_name: str,
    standard: dict[str, Any] | None,
) -> str | None:
    if standard is None:
        return None
    if standard.get("rename_to"):
        return str(standard["rename_to"])
    rename_suffix = standard.get("rename_suffix")
    if rename_suffix and column_name.lower().endswith(standard["match_key"]):
        prefix_length = len(column_name) - len(standard["match_key"])
        return column_name[:prefix_length] + str(rename_suffix)
    return None


def assess_change(
    column: dict[str, Any],
    standard: dict[str, Any] | None,
    foreign_keys: list[dict[str, Any]],
) -> tuple[str, str, str]:
    if standard is None:
        return "NO_STANDARD", "NONE", "No Metadata data type rule matched."

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
    metadata_target_id, rules = load_column_rules()
    standards = [rule for rule in rules if rule["sql_type"]]
    columns = load_columns(database_names)
    foreign_key_map = load_foreign_keys(database_names)
    role_by_database = {
        database_name: role
        for role, database_name in database_names.items()
    }

    results: list[dict[str, Any]] = []
    for column in columns:
        column_name = str(column["column_name"])
        matching_rules = find_matching_rules(column_name, rules)
        standard = match_type_standard(matching_rules)
        classification_source = "NAME_RULE" if standard else None
        if standard is None:
            standard = match_varchar_length_standard(column, rules)
            if standard:
                classification_source = "VARCHAR_LENGTH_BUCKET"
        recommended_name = recommended_column_name(column_name, standard)
        semantic_roles = list(
            dict.fromkeys(
                str(rule["semantic_role"])
                for rule in matching_rules
                if rule.get("semantic_role")
            )
        )
        if (
            standard
            and standard.get("semantic_role")
            and str(standard["semantic_role"]) not in semantic_roles
        ):
            semantic_roles.append(str(standard["semantic_role"]))
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
                    standard["match_key"]
                    if standard
                    and standard["match_type"] in {
                        "SUFFIX",
                        "COMPOUND_SUFFIX",
                    }
                    else None
                ),
                "matched_rule_type": (
                    standard["match_type"] if standard else None
                ),
                "matched_rule_key": (
                    standard["match_key"] if standard else None
                ),
                "match_priority": (
                    standard["priority"] if standard else None
                ),
                "classification_source": classification_source,
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
                "semantic_roles": semantic_roles,
                "semantic_role_text": ",".join(semantic_roles),
                "matching_rule_count": (
                    len(matching_rules)
                    + (
                        1
                        if standard
                        and standard["match_type"]
                        == "VARCHAR_LENGTH_BUCKET"
                        else 0
                    )
                ),
                "recommended_column_name": recommended_name,
                "naming_status": (
                    "RENAME_RECOMMENDED"
                    if recommended_name
                    and recommended_name.lower() != column_name.lower()
                    else "COMPLIANT"
                ),
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
            "rename_recommended": sum(
                item["naming_status"] == "RENAME_RECOMMENDED"
                for item in role_rows
            ),
        }

    return {
        "generated_dt": datetime.now().isoformat(timespec="seconds"),
        "read_only": True,
        "database_order": list(DATABASE_ROLES),
        "database_names": database_names,
        "metadata_target_id": metadata_target_id,
        "metadata_type_codes": sorted(
            {rule["metadata_type_code"] for rule in rules}
        ),
        "rule_count": len(rules),
        "standard_count": len(standards),
        "semantic_only_rule_count": sum(
            not rule["sql_type"] for rule in rules
        ),
        "varchar_length_bucket_rule_count": sum(
            rule["match_type"] == "VARCHAR_LENGTH_BUCKET"
            for rule in rules
        ),
        "rules": rules,
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


def write_csv(
    path: Path,
    report: dict[str, Any],
    rows: list[dict[str, Any]] | None = None,
) -> None:
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
        "matched_rule_type",
        "matched_rule_key",
        "match_priority",
        "classification_source",
        "semantic_role_text",
        "matching_rule_count",
        "recommended_column_name",
        "naming_status",
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
        output_rows = report["columns"] if rows is None else rows
        for item in output_rows:
            writer.writerow(
                {
                    field_name: item.get(field_name)
                    for field_name in field_names
                }
            )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare live Repository columns with sp_metadata semantic rules."
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
    mismatch_csv_path = (
        output_dir / f"{arguments.basename}_mismatch.csv"
    )

    write_json(json_path, report)
    write_csv(csv_path, report)
    write_csv(
        mismatch_csv_path,
        report,
        [
            item
            for item in report["columns"]
            if item["assessment_status"] == "MISMATCH"
        ],
    )

    summary = report["summary"]
    print("=" * 80)
    print("SPS Repository Data Type Inventory SUCCESS")
    print("=" * 80)
    print(f"Metadata target : {report['metadata_target_id']}")
    print(f"Rules           : {report['rule_count']}")
    print(f"Type standards  : {report['standard_count']}")
    print(f"Columns         : {summary['column_count']}")
    print(f"JSON            : {json_path}")
    print(f"CSV             : {csv_path}")
    print(f"Mismatch CSV    : {mismatch_csv_path}")
    print("-" * 80)
    for role in DATABASE_ROLES:
        item = summary["database_summary"][role]
        print(
            f"{role:<20} "
            f"columns={item['columns']:<5} "
            f"compliant={item['compliant']:<5} "
            f"mismatch={item['mismatch']:<5} "
            f"view={item['view_recreate_required']:<5} "
            f"no_standard={item['no_standard']:<5} "
            f"rename={item['rename_recommended']:<5}"
        )
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
