"""Audit every live *_code column against te_common.cm_common_code.

Read-only. Produces CSV and JSON reports classifying actual column values as:
CONFIRMED, AMBIGUOUS, PARTIAL, UNRESOLVED, or EMPTY.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase

DATABASE_ROLES = ("HEALTH_COMPANION", "STORY_PLATFORM", "COMMON")
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "reports"
DEFAULT_BASENAME = "repository_common_code_link_audit_20260720"
NAMESPACE_PREFIX_PATTERN = re.compile(
    r"^(?:AI|AU|CM|DC|EV|HC|HP|HS|MB|OC|RL|SP|SPS|WF)_"
)


def json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def quote_identifier(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


def database_names() -> dict[str, str]:
    result: dict[str, str] = {}
    for role in DATABASE_ROLES:
        database = CommonDatabase(database_role=role)
        try:
            result[role] = str(database.database_name)
        finally:
            database.close()
    return result


def load_code_columns(names: dict[str, str]) -> list[dict[str, Any]]:
    database = CommonDatabase(database_role="COMMON")
    try:
        placeholders = ", ".join(["%s"] * len(names))
        return database.fetch_all(
            f"""
            SELECT
                table_schema,
                table_name,
                column_name,
                column_type,
                is_nullable,
                column_default,
                column_comment
            FROM information_schema.columns
            WHERE table_schema IN ({placeholders})
              AND table_name NOT REGEXP '_backup_'
              AND column_name LIKE %s
            ORDER BY table_schema, table_name, ordinal_position
            """,
            (*names.values(), "%\\_code"),
        )
    finally:
        database.close()


def load_common_codes() -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    database = CommonDatabase(database_role="COMMON")
    try:
        rows = database.fetch_all(
            """
            SELECT group_code, code, status_code
            FROM cm_common_code
            WHERE deleted_dt IS NULL
            ORDER BY group_code, code
            """
        )
    finally:
        database.close()

    groups: dict[str, set[str]] = defaultdict(set)
    code_groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        group = str(row["group_code"])
        code = str(row["code"])
        groups[group].add(code)
        code_groups[code].append(group)
    return dict(groups), dict(code_groups)


def distinct_values(database: CommonDatabase, schema: str, table: str, column: str) -> list[str]:
    sql = (
        f"SELECT DISTINCT CAST({quote_identifier(column)} AS CHAR) AS code_value "
        f"FROM {quote_identifier(schema)}.{quote_identifier(table)} "
        f"WHERE {quote_identifier(column)} IS NOT NULL "
        f"AND TRIM(CAST({quote_identifier(column)} AS CHAR)) <> '' "
        f"ORDER BY code_value"
    )
    return [str(row["code_value"]) for row in database.fetch_all(sql)]


def semantic_tokens(column_name: str) -> set[str]:
    ignored = {"code", "status", "type"}
    return {token for token in column_name.lower().split("_") if token and token not in ignored}


def normalize_code_root(value: str) -> str:
    normalized = NAMESPACE_PREFIX_PATTERN.sub("", str(value).upper())
    return re.sub(r"_CODE$", "", normalized)


def rank_groups(column_name: str, candidates: list[str]) -> list[str]:
    tokens = semantic_tokens(column_name)

    def score(group: str) -> tuple[int, int, str]:
        upper = group.upper()
        hits = sum(1 for token in tokens if token.upper() in upper.split("_"))
        contains = sum(1 for token in tokens if token.upper() in upper)
        return (-hits, -contains, group)

    return sorted(candidates, key=score)


def analyze() -> dict[str, Any]:
    names = database_names()
    columns = load_code_columns(names)
    groups, code_groups = load_common_codes()
    role_by_schema = {schema: role for role, schema in names.items()}
    connections = {role: CommonDatabase(database_role=role) for role in DATABASE_ROLES}
    results: list[dict[str, Any]] = []

    try:
        for column in columns:
            schema = str(column["table_schema"])
            table = str(column["table_name"])
            name = str(column["column_name"])
            values = distinct_values(connections[role_by_schema[schema]], schema, table, name)
            value_set = set(values)

            column_root = normalize_code_root(name)
            name_exact = [
                group for group in groups if normalize_code_root(group) == column_root
            ]
            name_related = [
                group
                for group in groups
                if column_root in normalize_code_root(group)
                or normalize_code_root(group) in column_root
            ]
            value_exact = [
                group
                for group, codes in groups.items()
                if value_set and value_set <= codes
            ]
            compatible = [group for group in name_exact if group in value_exact]
            ranked_value_exact = rank_groups(name, value_exact)
            coverage = sorted(
                (
                    {
                        "group_code": group,
                        "matched_count": len(value_set & codes),
                        "total_value_count": len(value_set),
                        "coverage_pct": round(100 * len(value_set & codes) / len(value_set), 2),
                    }
                    for group, codes in groups.items()
                    if value_set and value_set & codes
                ),
                key=lambda item: (-item["matched_count"], item["group_code"]),
            )
            known_values = {value for value in values if value in code_groups}
            missing = sorted(value_set - known_values)

            if not values and name_exact:
                status = "EMPTY_NAME_LINKED"
            elif not values:
                status = "EMPTY_UNRESOLVED"
            elif len(compatible) == 1:
                status = "CONFIRMED"
            elif len(compatible) > 1:
                status = "AMBIGUOUS"
            elif name_exact:
                status = "NAME_LINK_VALUE_MISSING"
            elif len(ranked_value_exact) == 1:
                status = "VALUE_LINK_ONLY"
            elif len(ranked_value_exact) > 1:
                status = "AMBIGUOUS_VALUE_LINK"
            elif known_values:
                status = "PARTIAL"
            else:
                status = "UNRESOLVED"

            if len(compatible) == 1:
                recommended_group = compatible[0]
            elif len(ranked_value_exact) == 1:
                recommended_group = ranked_value_exact[0]
            elif not values and len(name_exact) == 1:
                recommended_group = name_exact[0]
            else:
                recommended_group = None

            results.append(
                {
                    "database_role": role_by_schema[schema],
                    "table_schema": schema,
                    "table_name": table,
                    "column_name": name,
                    "column_root": column_root,
                    "column_type": column["column_type"],
                    "column_comment": column.get("column_comment") or "",
                    "status": status,
                    "distinct_value_count": len(values),
                    "distinct_values": values,
                    "name_candidate_groups": sorted(name_exact),
                    "name_related_groups": sorted(name_related),
                    "value_candidate_groups": ranked_value_exact,
                    "candidate_groups": sorted(compatible) or ranked_value_exact,
                    "recommended_group": recommended_group,
                    "missing_common_code_values": missing,
                    "partial_group_coverage": coverage[:10],
                    "value_group_matches": {
                        value: sorted(code_groups.get(value, [])) for value in values
                    },
                }
            )
    finally:
        for database in connections.values():
            database.close()

    summary: dict[str, int] = defaultdict(int)
    for row in results:
        summary[row["status"]] += 1

    missing_occurrences = [
        {
            "database_role": row["database_role"],
            "table_schema": row["table_schema"],
            "table_name": row["table_name"],
            "column_name": row["column_name"],
            "missing_value": value,
        }
        for row in results
        for value in row["missing_common_code_values"]
    ]

    return {
        "database_names": names,
        "code_column_count": len(results),
        "summary": dict(sorted(summary.items())),
        "results": results,
        "missing_common_code_occurrences": missing_occurrences,
    }


def write_reports(report: dict[str, Any], output_dir: Path, basename: str) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{basename}.json"
    csv_path = output_dir / f"{basename}.csv"
    missing_path = output_dir / f"{basename}_missing_values.csv"

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=json_default) + "\n",
        encoding="utf-8",
    )

    fields = [
        "database_role", "table_schema", "table_name", "column_name", "column_root",
        "column_type", "status", "distinct_value_count", "distinct_values",
        "name_candidate_groups", "name_related_groups", "value_candidate_groups",
        "candidate_groups", "recommended_group", "missing_common_code_values",
        "column_comment",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["results"]:
            item = {key: row.get(key) for key in fields}
            for key in (
                "distinct_values",
                "name_candidate_groups",
                "name_related_groups",
                "value_candidate_groups",
                "candidate_groups",
                "missing_common_code_values",
            ):
                item[key] = "|".join(item[key] or [])
            writer.writerow(item)

    missing_fields = ["database_role", "table_schema", "table_name", "column_name", "missing_value"]
    with missing_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=missing_fields)
        writer.writeheader()
        writer.writerows(report["missing_common_code_occurrences"])

    return json_path, csv_path, missing_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--basename", default=DEFAULT_BASENAME)
    args = parser.parse_args()

    report = analyze()
    paths = write_reports(report, args.output_dir, args.basename)
    print("=" * 80)
    print("SPS Repository Common Code Link Audit SUCCESS")
    print("=" * 80)
    print(f"Code columns : {report['code_column_count']}")
    for status, count in report["summary"].items():
        print(f"{status:<12}: {count}")
    print(f"JSON         : {paths[0]}")
    print(f"CSV          : {paths[1]}")
    print(f"Missing CSV  : {paths[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
