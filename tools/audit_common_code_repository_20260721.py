"""Audit the complete SPS common-code repository.

Read-only. Audits every row in cm_common_code_group and cm_common_code and
writes machine-readable JSON/CSV evidence for the cleanup decision.
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

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "reports"
DEFAULT_BASENAME = "common_code_full_audit_20260721"
CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
GROUP_CODE_PATTERNS = {
    # ISO 639-1 language codes are intentionally lowercase.
    "LANGUAGE": re.compile(r"^[a-z]{2}$"),
    # BCP 47 language-region tags preserve lowercase language and uppercase region.
    "LOCALE": re.compile(r"^[a-z]{2}-[A-Z]{2}$"),
}
ALLOWED_STATUS_CODES = {"ACTIVE", "INACTIVE", "RETIRED", "HOLD"}


def json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def text_missing(value: Any) -> bool:
    return value is None or not str(value).strip()


def valid_code_format(group_code: str, code: str) -> bool:
    pattern = GROUP_CODE_PATTERNS.get(group_code, CODE_PATTERN)
    return pattern.fullmatch(code) is not None


def load_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    database = CommonDatabase(database_role="COMMON")
    try:
        groups = database.fetch_all(
            """
            SELECT *
            FROM cm_common_code_group
            ORDER BY group_code
            """
        )
        codes = database.fetch_all(
            """
            SELECT *
            FROM cm_common_code
            ORDER BY group_code, sort_no, code
            """
        )
        return groups, codes
    finally:
        database.close()


def audit(groups: list[dict[str, Any]], codes: list[dict[str, Any]]) -> dict[str, Any]:
    group_by_code = {str(row["group_code"]): row for row in groups}
    code_rows_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in codes:
        code_rows_by_group[str(row["group_code"])].append(row)

    group_issues: list[dict[str, Any]] = []
    for row in groups:
        group_code = str(row["group_code"])
        issues: list[str] = []
        if not CODE_PATTERN.fullmatch(group_code):
            issues.append("INVALID_GROUP_CODE_FORMAT")
        if text_missing(row.get("group_name")):
            issues.append("MISSING_GROUP_NAME")
        if text_missing(row.get("group_description")):
            issues.append("MISSING_GROUP_DESCRIPTION")
        if text_missing(row.get("program_id")):
            issues.append("MISSING_PROGRAM_ID")
        if row.get("status_code") not in ALLOWED_STATUS_CODES:
            issues.append("INVALID_STATUS_CODE")
        if row.get("deleted_dt") is not None and row.get("status_code") == "ACTIVE":
            issues.append("ACTIVE_WITH_DELETED_DT")
        if not code_rows_by_group.get(group_code):
            issues.append("EMPTY_GROUP")
        if issues:
            group_issues.append({"group_code": group_code, "issues": issues})

    code_issues: list[dict[str, Any]] = []
    group_summaries: list[dict[str, Any]] = []
    for group_code, rows in sorted(code_rows_by_group.items()):
        sort_counts = Counter(row.get("sort_no") for row in rows)
        name_counts = Counter(str(row.get("code_name") or "").strip() for row in rows)
        duplicate_sort_nos = sorted(
            value for value, count in sort_counts.items() if count > 1
        )
        duplicate_names = sorted(
            value for value, count in name_counts.items() if value and count > 1
        )
        for row in rows:
            issues: list[str] = []
            code = str(row["code"])
            if group_code not in group_by_code:
                issues.append("ORPHAN_GROUP")
            if not valid_code_format(group_code, code):
                issues.append("INVALID_CODE_FORMAT")
            if text_missing(row.get("code_name")):
                issues.append("MISSING_CODE_NAME")
            if text_missing(row.get("common_code_description")):
                issues.append("MISSING_DESCRIPTION")
            if text_missing(row.get("program_id")):
                issues.append("MISSING_PROGRAM_ID")
            if row.get("status_code") not in ALLOWED_STATUS_CODES:
                issues.append("INVALID_STATUS_CODE")
            if row.get("deleted_dt") is not None and row.get("status_code") == "ACTIVE":
                issues.append("ACTIVE_WITH_DELETED_DT")
            raw_json = row.get("common_code_json")
            if raw_json is not None:
                try:
                    json.loads(str(raw_json))
                except (TypeError, ValueError, json.JSONDecodeError):
                    issues.append("INVALID_COMMON_CODE_JSON")
            if row.get("sort_no") in duplicate_sort_nos:
                issues.append("DUPLICATE_SORT_NO")
            if str(row.get("code_name") or "").strip() in duplicate_names:
                issues.append("DUPLICATE_CODE_NAME")
            if issues:
                code_issues.append(
                    {"group_code": group_code, "code": code, "issues": issues}
                )

        group_summaries.append(
            {
                "group_code": group_code,
                "code_count": len(rows),
                "active_count": sum(r.get("status_code") == "ACTIVE" for r in rows),
                "retired_count": sum(r.get("status_code") == "RETIRED" for r in rows),
                "deleted_count": sum(r.get("deleted_dt") is not None for r in rows),
                "missing_description_count": sum(
                    text_missing(r.get("common_code_description")) for r in rows
                ),
                "missing_program_id_count": sum(
                    text_missing(r.get("program_id")) for r in rows
                ),
                "json_count": sum(r.get("common_code_json") is not None for r in rows),
                "duplicate_sort_nos": duplicate_sort_nos,
                "duplicate_code_names": duplicate_names,
            }
        )

    issue_counts = Counter(
        issue
        for item in group_issues + code_issues
        for issue in item["issues"]
    )
    return {
        "generated_dt": datetime.now().isoformat(timespec="seconds"),
        "database_role": "COMMON",
        "summary": {
            "group_count": len(groups),
            "code_count": len(codes),
            "active_group_count": sum(r.get("status_code") == "ACTIVE" for r in groups),
            "active_code_count": sum(r.get("status_code") == "ACTIVE" for r in codes),
            "retired_code_count": sum(r.get("status_code") == "RETIRED" for r in codes),
            "empty_group_count": sum(
                not code_rows_by_group.get(str(r["group_code"])) for r in groups
            ),
            "group_issue_count": len(group_issues),
            "code_issue_count": len(code_issues),
            "issue_counts": dict(sorted(issue_counts.items())),
        },
        "group_summaries": group_summaries,
        "group_issues": group_issues,
        "code_issues": code_issues,
        "groups": groups,
        "codes": codes,
    }


def write_reports(report: dict[str, Any], output_dir: Path, basename: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{basename}.json"
    csv_path = output_dir / f"{basename}_group_summary.csv"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=json_default) + "\n",
        encoding="utf-8",
    )
    fields = [
        "group_code", "code_count", "active_count", "retired_count",
        "deleted_count", "missing_description_count", "missing_program_id_count",
        "json_count", "duplicate_sort_nos", "duplicate_code_names",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["group_summaries"]:
            export = dict(row)
            export["duplicate_sort_nos"] = json.dumps(
                export["duplicate_sort_nos"], ensure_ascii=False
            )
            export["duplicate_code_names"] = json.dumps(
                export["duplicate_code_names"], ensure_ascii=False
            )
            writer.writerow(export)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(json_path)
    print(csv_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--basename", default=DEFAULT_BASENAME)
    args = parser.parse_args()
    groups, codes = load_rows()
    report = audit(groups, codes)
    write_reports(report, args.output_dir, args.basename)


if __name__ == "__main__":
    main()
