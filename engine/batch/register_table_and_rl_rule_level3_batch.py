"""Register Table Level 3 Rule and RL_RULE Level 3 classification children."""
from __future__ import annotations

import argparse
import json

from common.database import CommonDatabase
from engine.identifier import IdentifierCoordinator

PROGRAM_ID = "REGISTER_TABLE_AND_RL_RULE_LEVEL3_20260803"
CANONICAL_RULE_ID = "SP_RP_RL_RULE_20260731_00001"
MISTAKEN_RULE_ID = "CM_RL_TE_COMMON_RL_RULE_20260803_224412_00001"
TABLE_RULE_CODE = "RL_ALL_TABLE_LEVEL3_DEFAULT"


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


def insert_condition_action(common, coordinator, metadata, rule_id, field_code,
                            operator_code, condition_value, action_value,
                            sort_no, condition_remark, action_remark):
    condition_id = issue(coordinator, metadata["condition_id"])
    action_id = issue(coordinator, metadata["rule_action_id"])
    common.execute(
        """INSERT INTO rl_rule_condition (
           condition_id, rule_id, sort_no, field_code, operator_code, condition_value,
           remark, created_by, updated_by, program_id, client_ip, status_code
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (condition_id, rule_id, sort_no, field_code, operator_code, condition_value,
         condition_remark, "SYSTEM", "SYSTEM", PROGRAM_ID, "127.0.0.1", "ACTIVE"),
    )
    action_value["condition_id"] = condition_id
    common.execute(
        """INSERT INTO rl_rule_action (
           rule_action_id, rule_id, action_type_code, action_value, sort_no, remark,
           created_by, updated_by, program_id, client_ip, status_code
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (action_id, rule_id, "OBJECT_LEVEL_CLASSIFICATION",
         json.dumps(action_value, ensure_ascii=False, sort_keys=True),
         sort_no, action_remark, "SYSTEM", "SYSTEM", PROGRAM_ID, "127.0.0.1", "ACTIVE"),
    )
    return condition_id, action_id


def run(apply: bool) -> dict[str, object]:
    common = CommonDatabase(database_role="COMMON")
    story = CommonDatabase(database_role="STORY")
    try:
        existing_table_rule = common.fetch_one(
            "SELECT rule_id FROM rl_rule WHERE rule_code = %s AND deleted_dt IS NULL",
            (TABLE_RULE_CODE,),
        )
        canonical = common.fetch_one(
            "SELECT rule_id FROM rl_rule WHERE rule_id = %s AND deleted_dt IS NULL",
            (CANONICAL_RULE_ID,),
        )
        if not canonical:
            raise LookupError("Canonical SP_RP_RL_RULE was not found.")
        result: dict[str, object] = {
            "dry_run": not apply,
            "table_level3_rule_code": TABLE_RULE_CODE,
            "canonical_rule_id": CANONICAL_RULE_ID,
            "mistaken_rule_retire_id": MISTAKEN_RULE_ID,
            "table_level3_rule_exists": bool(existing_table_rule),
            "operations": [
                "retire mistaken CM rule and its children",
                "insert SP_RP_RL_RULE Table Level 3 default Rule",
                "insert RL_RULE Level 3 condition and action under canonical Rule",
            ],
        }
        if not apply:
            return result
        metadata = {str(row["object_code"]): row for row in story.fetch_all(
            """SELECT object_code, business_code, domain_code, object_level,
                      identifier_target_code, sequence_scope_code, sequence_length
               FROM sp_object
               WHERE object_code IN ('RL_RULE', 'TE_COMMON_RL_RULE_CONDITION', 'TE_COMMON_RL_RULE_ACTION')
                 AND active_yn = 'Y' AND status_code = 'ACTIVE' AND deleted_dt IS NULL"""
        )}
        required = {"RL_RULE", "TE_COMMON_RL_RULE_CONDITION", "TE_COMMON_RL_RULE_ACTION"}
        if set(metadata) != required:
            raise LookupError("Level 3 Rule Identifier metadata is incomplete.")
        child_metadata = {
            "condition_id": metadata["TE_COMMON_RL_RULE_CONDITION"],
            "rule_action_id": metadata["TE_COMMON_RL_RULE_ACTION"],
        }
        coordinator = IdentifierCoordinator(story)
        common.begin()
        story.begin()
        try:
            for table_name, id_column in (
                ("rl_rule_action", "rule_action_id"),
                ("rl_rule_condition", "condition_id"),
                ("rl_rule", "rule_id"),
            ):
                common.execute(
                    f"""UPDATE {table_name}
                        SET deleted_by = %s, deleted_dt = CURRENT_TIMESTAMP,
                            updated_by = %s, program_id = %s, client_ip = %s
                        WHERE {id_column} = %s AND deleted_dt IS NULL""",
                    ("SYSTEM", "SYSTEM", PROGRAM_ID, "127.0.0.1",
                     MISTAKEN_RULE_ID if table_name == "rl_rule" else
                     ("CM_RL_TE_COMMON_RL_RULE_ACTION_20260803_224412_00001"
                      if table_name == "rl_rule_action"
                      else "CM_RL_TE_COMMON_RL_RULE_CONDITION_20260803_224412_00001")),
                )
            if existing_table_rule:
                table_rule_id = existing_table_rule["rule_id"]
            else:
                table_rule_id = issue(coordinator, metadata["RL_RULE"])
                common.execute(
                    """INSERT INTO rl_rule (
                       rule_id, rule_code, rule_name, rule_type_code, rule_group_code,
                       rule_description, priority_no, status_code, version_num, remark, sort_no,
                       created_by, updated_by, program_id, client_ip
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (table_rule_id, TABLE_RULE_CODE, "SPS 모든 Table Level 3 규칙",
                     "LIFECYCLE", "OBJECT_LEVEL", "모든 Table Object는 Level 3이다.",
                     110, "ACTIVE", "1.0", "DEFAULT_TABLE_OBJECT_LEVEL=3", 20,
                     "SYSTEM", "SYSTEM", PROGRAM_ID, "127.0.0.1"),
                )
                insert_condition_action(
                    common, coordinator, child_metadata, table_rule_id,
                    "rule_resolution_source", "EQ", "DEFAULT",
                    {"action_type_group_code": "ACTION_TYPE",
                     "condition_context": {"object_type_code": "TABLE",
                                           "rule_resolution_source": "DEFAULT"},
                     "default_object_level": 3, "resolution_order": ["DEFAULT"]},
                    10, "Table Level 3 Default Action 전용 Negative Condition.",
                    "Negative Condition이 일치할 때 Rule 등록 기본 Level 3을 반환하는 Default Action.",
                )
            rl_rule_condition_id, rl_rule_action_id = insert_condition_action(
                common, coordinator, child_metadata, CANONICAL_RULE_ID,
                "object_code", "EQ", "RL_RULE",
                {"action_type_group_code": "ACTION_TYPE", "object_level": 3,
                 "resolution_order": ["EXPLICIT_RULE"]},
                60, "RL_RULE Table Object Level 3 명시 Condition.",
                "RL_RULE Table Object의 rule_id 발급 레벨 3을 반환하는 Action.",
            )
            common.commit()
            story.commit()
        except Exception:
            common.rollback()
            story.rollback()
            raise
        result.update(dry_run=False, table_rule_id=table_rule_id,
                      rl_rule_condition_id=rl_rule_condition_id,
                      rl_rule_action_id=rl_rule_action_id)
        return result
    finally:
        common.close()
        story.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    print(json.dumps(run(parser.parse_args().apply), ensure_ascii=False, indent=2))
