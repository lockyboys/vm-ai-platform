# =============================================================================
# File Name : tools/generate_repository_level4_id_migration_20260721.py
# Purpose   : Generate the one-time Level 4 migration map and SQL batch
# =============================================================================
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase

SCHEMAS = ("te_health_companion", "te_story_platform", "te_common")
ROLE = "COMMON"
OUTPUT_SQL = PROJECT_ROOT / "sql/runtime/repository_level4_id_migration_20260721.sql"
OUTPUT_CSV = PROJECT_ROOT / "outputs/reports/repository_level4_id_migration_map_20260721.csv"
HOLD_CSV = PROJECT_ROOT / "outputs/reports/repository_level4_id_migration_hold_20260721.csv"
LEVEL4 = re.compile(r"^[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9_]+_[0-9]{8}_[0-9]{6}_[0-9]{5}$")
AUDIT_COLUMNS = {"created_by", "updated_by", "deleted_by", "client_ip"}
POLYMORPHIC_COLUMNS = {"source_object_id", "target_object_id", "target_id", "target_record_id", "action_target_id"}
PREFIX_ALIAS = {"source_", "target_", "parent_", "representative_"}
DOMAIN_BY_PREFIX = {
    "cm": "CM", "ev": "EV", "rl": "RL", "sql_guard": "SG",
    "system": "SY", "sp_policy": "RL", "ac": "AC", "at": "AT",
    "dc": "DC", "fb": "FB", "sp": "RP", "md": "MT",
}
SPECIAL_DOMAIN = {
    ("te_story_platform", "sp_metadata"): "MT",
    ("te_story_platform", "sp_identifier_blueprint"): "ID",
    ("te_story_platform", "sp_identifier_sequence"): "ID",
}
BUSINESS_BY_SCHEMA = {
    "te_common": "CM",
    "te_health_companion": "HC",
    "te_story_platform": "SP",
}

def q(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"

def s(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"

def canonical_column(name: str) -> str:
    value = name
    changed = True
    while changed:
        changed = False
        for prefix in PREFIX_ALIAS:
            if value.startswith(prefix):
                value = value[len(prefix):]
                changed = True
    return value

def object_code(column: str) -> str:
    value = canonical_column(column)
    if value.endswith("_id"):
        value = value[:-3]
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_") or "OBJECT"

def domain_code(schema: str, table: str) -> str:
    if (schema, table) in SPECIAL_DOMAIN:
        return SPECIAL_DOMAIN[(schema, table)]
    for prefix in sorted(DOMAIN_BY_PREFIX, key=len, reverse=True):
        if table == prefix or table.startswith(prefix + "_"):
            return DOMAIN_BY_PREFIX[prefix]
    return "RP"

def backup_name(table: str) -> str:
    suffix = "_bkp_l4_20260721"
    return table[:64-len(suffix)] + suffix

def main() -> None:
    db = CommonDatabase(database_role=ROLE)
    try:
        placeholders = ", ".join(["%s"] * len(SCHEMAS))
        columns = db.fetch_all(
            f"""
            SELECT c.table_schema, c.table_name, c.column_name,
                   c.column_key, c.is_nullable
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON t.table_schema=c.table_schema AND t.table_name=c.table_name
            WHERE c.table_schema IN ({placeholders})
              AND t.table_type='BASE TABLE'
              AND c.column_name LIKE '%%\\_id'
              AND c.table_name NOT LIKE '%%\\_backup\\_%%'
              AND c.table_name NOT LIKE '%%\\_bkp\\_%%'
            ORDER BY c.table_schema, c.table_name, c.ordinal_position
            """,
            SCHEMAS,
        )

        fks = db.fetch_all(
            f"""
            SELECT constraint_schema, table_name, constraint_name, column_name,
                   referenced_table_schema, referenced_table_name,
                   referenced_column_name
            FROM information_schema.key_column_usage
            WHERE constraint_schema IN ({placeholders})
              AND referenced_table_name IS NOT NULL
            ORDER BY constraint_schema, table_name, constraint_name, ordinal_position
            """,
            SCHEMAS,
        )

        # Union-Find connects physical references and semantic source/target/parent aliases.
        keys = {(r["table_schema"], r["table_name"], r["column_name"]) for r in columns}
        parent = {k: k for k in keys}
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            if a in parent and b in parent:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra

        for fk in fks:
            union(
                (fk["constraint_schema"], fk["table_name"], fk["column_name"]),
                (fk["referenced_table_schema"], fk["referenced_table_name"], fk["referenced_column_name"]),
            )
        by_canonical = defaultdict(list)
        for key in keys:
            if key[2] not in POLYMORPHIC_COLUMNS:
                by_canonical[canonical_column(key[2])].append(key)
        for members in by_canonical.values():
            for member in members[1:]:
                union(members[0], member)

        groups = defaultdict(list)
        for key in keys:
            groups[find(key)].append(key)

        component_code = {
            root: canonical_column(sorted(members)[0][2]).upper()
            for root, members in groups.items()
        }

        invalid_columns = []
        for row in columns:
            key = (row["table_schema"], row["table_name"], row["column_name"])
            count = db.fetch_one(
                f"""SELECT COUNT(*) AS c FROM {q(key[0])}.{q(key[1])}
                    WHERE {q(key[2])} IS NOT NULL
                      AND CAST({q(key[2])} AS CHAR) <> ''
                      AND CAST({q(key[2])} AS CHAR) NOT REGEXP
                          '^[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9_]+_[0-9]{{8}}_[0-9]{{6}}_[0-9]{{5}}$'"""
            )["c"]
            if int(count):
                root = find(key)
                invalid_columns.append({
                    **row,
                    "invalid_count": int(count),
                    "group": root,
                    "group_code": component_code[root],
                })

        affected_groups = {r["group"] for r in invalid_columns}
        map_rows, holds = [], []
        generation_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        for root in sorted(affected_groups):
            members = groups[root]
            canonical = component_code[root].lower()
            values = {}
            for schema, table, column in members:
                if column in AUDIT_COLUMNS or column in POLYMORPHIC_COLUMNS:
                    continue
                created_exists = db.fetch_one(
                    """SELECT COUNT(*) AS c FROM information_schema.columns
                       WHERE table_schema=%s AND table_name=%s AND column_name='created_dt'""",
                    (schema, table),
                )["c"]
                created_expr = "MIN(created_dt)" if int(created_exists) else "NULL"
                rows = db.fetch_all(
                    f"""SELECT CAST({q(column)} AS CHAR) AS old_id,
                               {created_expr} AS created_dt
                        FROM {q(schema)}.{q(table)}
                        WHERE {q(column)} IS NOT NULL
                          AND CAST({q(column)} AS CHAR) <> ''
                          AND CAST({q(column)} AS CHAR) NOT REGEXP
                              '^[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9_]+_[0-9]{{8}}_[0-9]{{6}}_[0-9]{{5}}$'
                        GROUP BY CAST({q(column)} AS CHAR)"""
                )
                for item in rows:
                    old = str(item["old_id"])
                    dt = item.get("created_dt")
                    current = values.get(old)
                    if current is None or (dt is not None and (current is None or dt < current)):
                        values[old] = dt

            representative = sorted(members)[0]
            business = BUSINESS_BY_SCHEMA[representative[0]]
            domain = domain_code(representative[0], representative[1])
            obj = object_code(canonical)
            for sequence, old in enumerate(sorted(values), 1):
                dt = values[old]
                stamp = dt.strftime("%Y%m%d_%H%M%S") if hasattr(dt, "strftime") else generation_time
                new = f"{business}_{domain}_{obj}_{stamp}_{sequence:05d}"
                if len(new) > 99:
                    holds.append({"group": canonical, "old_id": old, "reason": "NEW_ID_EXCEEDS_VARCHAR_99"})
                    continue
                map_rows.append({
                    "group_code": canonical.upper(),
                    "old_id": old,
                    "new_id": new,
                    "member_count": len(members),
                })

        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=["group_code", "old_id", "new_id", "member_count"])
            writer.writeheader()
            writer.writerows(map_rows)
        with HOLD_CSV.open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=["group", "old_id", "reason"])
            writer.writeheader()
            writer.writerows(holds)

        affected_tables = sorted({(r["table_schema"], r["table_name"]) for r in invalid_columns})
        sql = [
            "/* Repository Level 4 ID Migration 20260721",
            f"Affected columns: {len(invalid_columns)}",
            f"Affected tables: {len(affected_tables)}",
            f"Map rows: {len(map_rows)}",
            f"Hold rows: {len(holds)}",
            "*/",
            "SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS;",
            "SET FOREIGN_KEY_CHECKS = 0;",
        ]
        for schema, table in affected_tables:
            backup = backup_name(table)
            sql += [
                f"CREATE TABLE IF NOT EXISTS {q(schema)}.{q(backup)} LIKE {q(schema)}.{q(table)};",
                f"INSERT INTO {q(schema)}.{q(backup)} SELECT * FROM {q(schema)}.{q(table)} "
                f"WHERE NOT EXISTS (SELECT 1 FROM {q(schema)}.{q(backup)} LIMIT 1);",
            ]
        sql += [
            "DROP TEMPORARY TABLE IF EXISTS tmp_repository_level4_id_map;",
            """CREATE TEMPORARY TABLE tmp_repository_level4_id_map (
  group_code VARCHAR(99) NOT NULL,
  old_id VARCHAR(99) NOT NULL,
  new_id VARCHAR(99) NOT NULL,
  PRIMARY KEY (group_code, old_id),
  UNIQUE KEY uk_tmp_level4_new_id (new_id)
) ENGINE=InnoDB;""",
        ]
        chunk_size = 250
        for start in range(0, len(map_rows), chunk_size):
            chunk = map_rows[start:start+chunk_size]
            values_sql = ",\n".join(
                f"({s(x['group_code'])}, {s(x['old_id'])}, {s(x['new_id'])})" for x in chunk
            )
            sql.append(
                "INSERT INTO tmp_repository_level4_id_map "
                "(group_code, old_id, new_id) VALUES\n" + values_sql + ";"
            )

        # Polymorphic logical references reuse an unambiguous real Object ID.
        for row in invalid_columns:
            if row["column_name"] not in POLYMORPHIC_COLUMNS:
                continue
            key = (row["table_schema"], row["table_name"], row["column_name"])
            sql.append(
                f"UPDATE {q(key[0])}.{q(key[1])} t "
                "JOIN (SELECT old_id, MIN(new_id) AS new_id "
                "FROM tmp_repository_level4_id_map GROUP BY old_id "
                "HAVING COUNT(DISTINCT new_id)=1) m "
                f"ON BINARY m.old_id=BINARY CAST(t.{q(key[2])} AS CHAR) "
                f"SET t.{q(key[2])}=m.new_id;"
            )

        # Child/reference columns first, PK columns last; FK checks remain disabled until validation.
        ordered = sorted(
            invalid_columns,
            key=lambda r: (r["column_key"] == "PRI", r["table_schema"], r["table_name"], r["column_name"]),
        )
        seen = set()
        for row in ordered:
            key = (row["table_schema"], row["table_name"], row["column_name"])
            if key in seen or row["column_name"] in POLYMORPHIC_COLUMNS:
                continue
            seen.add(key)
            group_code = row["group_code"]
            sql.append(
                f"UPDATE {q(key[0])}.{q(key[1])} t "
                f"JOIN tmp_repository_level4_id_map m "
                f"ON m.group_code={s(group_code)} AND BINARY m.old_id=BINARY CAST(t.{q(key[2])} AS CHAR) "
                f"SET t.{q(key[2])}=m.new_id;"
            )

        sql += [
            "SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;",
            """SELECT COUNT(*) AS migration_map_count
FROM tmp_repository_level4_id_map;""",
        ]
        for row in invalid_columns:
            sql.append(
                f"SELECT {s(row['table_schema'])} AS table_schema, "
                f"{s(row['table_name'])} AS table_name, {s(row['column_name'])} AS column_name, "
                f"COUNT(*) AS invalid_count FROM {q(row['table_schema'])}.{q(row['table_name'])} "
                f"WHERE {q(row['column_name'])} IS NOT NULL "
                f"AND CAST({q(row['column_name'])} AS CHAR) <> '' "
                f"AND CAST({q(row['column_name'])} AS CHAR) NOT REGEXP "
                f"'^[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9_]+_[0-9]{{8}}_[0-9]{{6}}_[0-9]{{5}}$';"
            )
        OUTPUT_SQL.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_SQL.write_text("\n\n".join(sql) + "\n", encoding="utf-8")
        print(f"OUTPUT_SQL={OUTPUT_SQL.relative_to(PROJECT_ROOT)}")
        print(f"MAP_CSV={OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
        print(f"HOLD_CSV={HOLD_CSV.relative_to(PROJECT_ROOT)}")
        print(f"AFFECTED_TABLES={len(affected_tables)}")
        print(f"AFFECTED_COLUMNS={len(invalid_columns)}")
        print(f"MAP_ROWS={len(map_rows)}")
        print(f"HOLD_ROWS={len(holds)}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
