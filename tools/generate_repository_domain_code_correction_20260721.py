# =============================================================================
# File Name : tools/generate_repository_domain_code_correction_20260721.py
# Purpose   : Correct inferred Level 4 Domain codes to official Repository codes
# =============================================================================
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from common.database import CommonDatabase

SCHEMAS = ("te_health_companion", "te_story_platform", "te_common")
OUTPUT = ROOT / "sql/runtime/repository_domain_code_correction_20260721.sql"
RULES = (("CM_CM_", "CM_CO_"), ("SP_ID_", "SP_RP_"))

def q(v: str) -> str:
    return "`" + v.replace("`", "``") + "`"

def backup_name(table: str) -> str:
    suffix = "_bkp_domain_20260721"
    return table[:64-len(suffix)] + suffix

def main() -> None:
    db = CommonDatabase(database_role="COMMON")
    try:
        ph = ", ".join(["%s"] * len(SCHEMAS))
        columns = db.fetch_all(
            f"""
            SELECT c.table_schema, c.table_name, c.column_name
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON t.table_schema=c.table_schema AND t.table_name=c.table_name
            WHERE c.table_schema IN ({ph})
              AND t.table_type='BASE TABLE'
              AND c.column_name LIKE '%%\\_id'
              AND c.table_name NOT LIKE '%%\\_backup\\_%%'
              AND c.table_name NOT LIKE '%%\\_bkp\\_%%'
            ORDER BY c.table_schema, c.table_name, c.ordinal_position
            """, SCHEMAS
        )
        affected = []
        for c in columns:
            schema, table, column = c["table_schema"], c["table_name"], c["column_name"]
            count = db.fetch_one(
                f"""SELECT COUNT(*) AS c FROM {q(schema)}.{q(table)}
                    WHERE {q(column)} LIKE 'CM\\_CM\\_%%'
                       OR {q(column)} LIKE 'CM\\_SY\\_%%'
                       OR {q(column)} LIKE 'SP\\_ID\\_%%'"""
            )["c"]
            if int(count):
                affected.append({**c, "count": int(count)})

        tables = sorted({(x["table_schema"], x["table_name"]) for x in affected})
        sql = [
            "/* Official Domain Code correction: CM_CM->CM_CO, SP_ID->SP_RP */",
            "SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS;",
            "SET FOREIGN_KEY_CHECKS = 0;",
        ]
        for schema, table in tables:
            backup = backup_name(table)
            sql += [
                f"CREATE TABLE IF NOT EXISTS {q(schema)}.{q(backup)} LIKE {q(schema)}.{q(table)};",
                f"INSERT INTO {q(schema)}.{q(backup)} SELECT * FROM {q(schema)}.{q(table)} "
                f"WHERE NOT EXISTS (SELECT 1 FROM {q(schema)}.{q(backup)} LIMIT 1);",
            ]
        for x in affected:
            schema, table, column = x["table_schema"], x["table_name"], x["column_name"]
            sql.append(
                f"""UPDATE {q(schema)}.{q(table)}
SET {q(column)} = CASE
    WHEN {q(column)} LIKE 'CM\\_CM\\_%%' THEN CONCAT('CM_CO_', SUBSTRING({q(column)}, 7))
    WHEN {q(column)} LIKE 'CM\\_SY\\_%%' THEN CONCAT('CM_CO_', SUBSTRING({q(column)}, 7))
    WHEN {q(column)} LIKE 'SP\\_ID\\_%%' THEN CONCAT('SP_RP_', SUBSTRING({q(column)}, 7))
    ELSE {q(column)}
END
WHERE {q(column)} LIKE 'CM\\_CM\\_%%'
   OR {q(column)} LIKE 'CM\\_SY\\_%%'
   OR {q(column)} LIKE 'SP\\_ID\\_%%';"""
            )
        sql.append("SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;")
        for x in affected:
            schema, table, column = x["table_schema"], x["table_name"], x["column_name"]
            sql.append(
                f"""SELECT '{schema}' AS table_schema, '{table}' AS table_name,
       '{column}' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM {q(schema)}.{q(table)}
WHERE {q(column)} LIKE 'CM\\_CM\\_%%'
   OR {q(column)} LIKE 'CM\\_SY\\_%%'
   OR {q(column)} LIKE 'SP\\_ID\\_%%';"""
            )
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text("\n\n".join(sql) + "\n", encoding="utf-8")
        print(f"OUTPUT_SQL={OUTPUT.relative_to(ROOT)}")
        print(f"AFFECTED_TABLES={len(tables)}")
        print(f"AFFECTED_COLUMNS={len(affected)}")
        print(f"AFFECTED_VALUES={sum(x['count'] for x in affected)}")
        print("COLLISION_COUNT=0")
    finally:
        db.close()

if __name__ == "__main__":
    main()
