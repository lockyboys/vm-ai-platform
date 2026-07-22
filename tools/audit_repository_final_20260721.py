"""Read-only final Repository audit before backup cleanup."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.database import CommonDatabase

SCHEMAS = ("te_common", "te_health_companion", "te_story_platform")
BACKUP_RE = re.compile(r"(_bkp_|_backup_)", re.I)
LEVEL4_RE = r"^[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9_]+_[0-9]{8}_[0-9]{6}_[0-9]{5}$"
REPORT = ROOT / "outputs/reports/repository_final_audit_20260721.json"


def qi(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


def main() -> int:
    db = CommonDatabase(database_role="COMMON")
    placeholders = ", ".join(["%s"] * len(SCHEMAS))
    try:
        tables = db.fetch_all(
            f"""SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema IN ({placeholders})
                ORDER BY table_schema, table_name""",
            SCHEMAS,
        )
        live_tables = [
            row for row in tables
            if row["table_type"] == "BASE TABLE"
            and not BACKUP_RE.search(row["table_name"])
        ]
        backup_tables = [
            row for row in tables
            if row["table_type"] == "BASE TABLE"
            and BACKUP_RE.search(row["table_name"])
        ]

        columns = db.fetch_all(
            f"""SELECT table_schema, table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema IN ({placeholders})
                  AND column_name LIKE %s
                ORDER BY table_schema, table_name, ordinal_position""",
            (*SCHEMAS, "%\\_id"),
        )
        live_names = {(r["table_schema"], r["table_name"]) for r in live_tables}
        id_columns = [
            row for row in columns
            if (row["table_schema"], row["table_name"]) in live_names
            and row["data_type"] in ("char", "varchar", "tinytext", "text", "mediumtext", "longtext")
        ]

        level4_violations = []
        legacy_prefix_violations = []
        for col in id_columns:
            s, t, c = col["table_schema"], col["table_name"], col["column_name"]
            row = db.fetch_one(
                f"""SELECT
                       SUM(CASE WHEN {qi(c)} IS NOT NULL
                                 AND {qi(c)} <> ''
                                 AND {qi(c)} NOT REGEXP %s
                                THEN 1 ELSE 0 END) AS invalid_count,
                       SUM(CASE WHEN {qi(c)} LIKE 'CM\\\\_CM\\\\_%%'
                                  OR {qi(c)} LIKE 'SP\\\\_ID\\\\_%%'
                                THEN 1 ELSE 0 END) AS legacy_count
                    FROM {qi(s)}.{qi(t)}""",
                (LEVEL4_RE,),
            )
            invalid_count = int(row["invalid_count"] or 0)
            legacy_count = int(row["legacy_count"] or 0)
            if invalid_count:
                level4_violations.append({**col, "invalid_count": invalid_count})
            if legacy_count:
                legacy_prefix_violations.append({**col, "legacy_count": legacy_count})

        fk_rows = db.fetch_all(
            f"""SELECT
                    k.constraint_schema, k.constraint_name,
                    k.table_name, k.column_name, k.ordinal_position,
                    k.referenced_table_schema, k.referenced_table_name,
                    k.referenced_column_name
                FROM information_schema.key_column_usage k
                WHERE k.constraint_schema IN ({placeholders})
                  AND k.referenced_table_name IS NOT NULL
                ORDER BY k.constraint_schema, k.table_name,
                         k.constraint_name, k.ordinal_position""",
            SCHEMAS,
        )
        grouped = {}
        for row in fk_rows:
            key = (row["constraint_schema"], row["table_name"], row["constraint_name"])
            grouped.setdefault(key, []).append(row)

        fk_orphans = []
        for (schema, table, constraint), parts in grouped.items():
            parent_schema = parts[0]["referenced_table_schema"]
            parent_table = parts[0]["referenced_table_name"]
            join = " AND ".join(
                f"c.{qi(p['column_name'])}=p.{qi(p['referenced_column_name'])}"
                for p in parts
            )
            present = " AND ".join(f"c.{qi(p['column_name'])} IS NOT NULL" for p in parts)
            missing = f"p.{qi(parts[0]['referenced_column_name'])} IS NULL"
            row = db.fetch_one(
                f"""SELECT COUNT(*) AS orphan_count
                    FROM {qi(schema)}.{qi(table)} c
                    LEFT JOIN {qi(parent_schema)}.{qi(parent_table)} p ON {join}
                    WHERE {present} AND {missing}"""
            )
            count = int(row["orphan_count"] or 0)
            if count:
                fk_orphans.append({
                    "constraint_schema": schema,
                    "table_name": table,
                    "constraint_name": constraint,
                    "referenced_table_schema": parent_schema,
                    "referenced_table_name": parent_table,
                    "orphan_count": count,
                })

        code_checks = {
            "invalid_rule_action_type_count": """
                SELECT COUNT(*) AS cnt FROM te_common.rl_rule_action r
                LEFT JOIN te_common.cm_common_code c
                  ON c.group_code='ACTION_TYPE'
                 AND c.code=r.action_type_code COLLATE utf8mb4_unicode_ci
                WHERE c.code IS NULL""",
            "invalid_action_type_count": """
                SELECT COUNT(*) AS cnt FROM te_health_companion.ac_action a
                LEFT JOIN te_common.cm_common_code c
                  ON c.group_code='ACTION_TYPE'
                 AND c.code=a.action_type_code COLLATE utf8mb4_unicode_ci
                WHERE c.code IS NULL""",
            "invalid_result_count": """
                SELECT COUNT(*) AS cnt FROM te_health_companion.ac_action a
                LEFT JOIN te_common.cm_common_code c
                  ON c.group_code='CM_JOB_STATUS'
                 AND c.code=a.result_code COLLATE utf8mb4_unicode_ci
                WHERE a.result_code IS NOT NULL AND c.code IS NULL""",
            "invalid_audit_result_count": """
                SELECT COUNT(*) AS cnt FROM te_health_companion.at_audit a
                LEFT JOIN te_common.cm_common_code c
                  ON c.group_code='CM_JOB_STATUS'
                 AND c.code=a.audit_result_code COLLATE utf8mb4_unicode_ci
                WHERE c.code IS NULL""",
            "invalid_ai_provider_count": """
                SELECT COUNT(*) AS cnt FROM te_health_companion.at_audit a
                LEFT JOIN te_common.cm_common_code c
                  ON c.group_code='AI_PROVIDER'
                 AND c.code=a.ai_provider_code COLLATE utf8mb4_unicode_ci
                WHERE a.ai_provider_code IS NOT NULL AND c.code IS NULL""",
            "invalid_decision_type_count": """
                SELECT COUNT(*) AS cnt FROM te_health_companion.dc_decision d
                LEFT JOIN te_common.cm_common_code c
                  ON c.group_code='DECISION_TYPE'
                 AND c.code=d.decision_type_code COLLATE utf8mb4_unicode_ci
                WHERE c.code IS NULL""",
        }
        common_code_violations = {
            name: int(db.fetch_one(sql)["cnt"])
            for name, sql in code_checks.items()
        }

        report = {
            "status": "PASS",
            "live_table_count": len(live_tables),
            "backup_table_count": len(backup_tables),
            "id_column_count": len(id_columns),
            "foreign_key_count": len(grouped),
            "level4_violations": level4_violations,
            "legacy_prefix_violations": legacy_prefix_violations,
            "foreign_key_orphans": fk_orphans,
            "common_code_violations": common_code_violations,
        }
        if (
            level4_violations
            or legacy_prefix_violations
            or fk_orphans
            or any(common_code_violations.values())
        ):
            report["status"] = "FAILED"

        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        print(f"REPORT={REPORT.relative_to(ROOT)}")
        return 0 if report["status"] == "PASS" else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
