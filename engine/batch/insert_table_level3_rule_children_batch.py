"""Insert Table Level 3 DEFAULT Rule children under the canonical Rule."""
from __future__ import annotations

import argparse
import json

from common.database import CommonDatabase
from engine.identifier import IdentifierCoordinator

PROGRAM_ID = "INSERT_TABLE_LEVEL3_RULE_CHILDREN_20260803"
RULE_ID = "SP_RP_RL_RULE_20260731_00001"


def issue(coordinator, metadata):
    request, prepared = coordinator.prepare_registered_object(
        object_metadata=metadata, created_by="SYSTEM", updated_by="SYSTEM",
        client_ip="127.0.0.1", program_id=PROGRAM_ID,
    )
    coordinator.acquire(prepared)
    try:
        return coordinator.resolve(request=request, prepared=prepared).identifier
    finally:
        coordinator.release(prepared)


def run(apply: bool) -> dict[str, object]:
    common = CommonDatabase(database_role="COMMON")
    story = CommonDatabase(database_role="STORY")
    try:
        rule = common.fetch_one(
            "SELECT rule_id FROM rl_rule WHERE rule_id = %s AND deleted_dt IS NULL",
            (RULE_ID,),
        )
        exists = common.fetch_one(
            """SELECT condition_id FROM rl_rule_condition
               WHERE rule_id = %s AND field_code = 'rule_resolution_source'
                 AND operator_code = 'EQ' AND condition_value = 'DEFAULT'
                 AND deleted_dt IS NULL""",
            (RULE_ID,),
        )
        result: dict[str, object] = {
            "dry_run": not apply,
            "rule_id": RULE_ID,
            "default_condition_exists": bool(exists),
        }
        if not rule:
            raise LookupError("Canonical rl_rule was not found.")
        if exists or not apply:
            return result

        metadata = {row["target_identifier_field"]: row for row in story.fetch_all(
            """SELECT object_code, business_code, domain_code, object_level,
                      identifier_target_code, sequence_scope_code, sequence_length,
                      target_identifier_field
               FROM sp_object
               WHERE target_identifier_field IN ('condition_id', 'rule_action_id')
                 AND active_yn = 'Y' AND status_code = 'ACTIVE' AND deleted_dt IS NULL"""
        )}
        if set(metadata) != {"condition_id", "rule_action_id"}:
            raise LookupError("Rule child Identifier metadata is incomplete.")
        coordinator = IdentifierCoordinator(story)
        common.begin()
        story.begin()
        try:
            condition_id = issue(coordinator, metadata["condition_id"])
            action_id = issue(coordinator, metadata["rule_action_id"])
            common.execute(
                """INSERT INTO rl_rule_condition (
                   condition_id, rule_id, sort_no, field_code, operator_code, condition_value,
                   remark, created_by, updated_by, program_id, client_ip, status_code
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (condition_id, RULE_ID, 40, "rule_resolution_source", "EQ", "DEFAULT",
                 "명시 Table Level Condition이 일치하지 않을 때 DEFAULT를 제공하는 Negative Condition.",
                 "SYSTEM", "SYSTEM", PROGRAM_ID, "127.0.0.1", "ACTIVE"),
            )
            common.execute(
                """INSERT INTO rl_rule_action (
                   rule_action_id, rule_id, action_type_code, action_value, sort_no, remark,
                   created_by, updated_by, program_id, client_ip, status_code
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (action_id, RULE_ID, "OBJECT_LEVEL_CLASSIFICATION", json.dumps({
                    "action_type_group_code": "ACTION_TYPE",
                    "condition_id": condition_id,
                    "condition_context": {
                        "object_type_code": "TABLE",
                        "rule_resolution_source": "DEFAULT",
                    },
                    "default_object_level": 3,
                    "resolution_order": ["DEFAULT"],
                 }, ensure_ascii=False, sort_keys=True), 40,
                 "Negative Condition이 일치할 때 Rule 등록 기본 Level 3을 반환하는 Default Action.",
                 "SYSTEM", "SYSTEM", PROGRAM_ID, "127.0.0.1", "ACTIVE"),
            )
            common.commit()
            story.commit()
        except Exception:
            common.rollback()
            story.rollback()
            raise
        result.update(dry_run=False, condition_id=condition_id, rule_action_id=action_id,
                      condition_inserted_rows=1, action_inserted_rows=1)
        return result
    finally:
        common.close()
        story.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    print(json.dumps(run(parser.parse_args().apply), ensure_ascii=False, indent=2))
