/*
 * Repository Identifier Object Level contract migration.
 *
 * ERD is the Level 2 grouping of Level 3 Table Objects.
 * Relationship is the Level 3 grouping of Level 4 Attributes.
 * This changes metadata only; it does not alter any table schema.
 */
USE te_common;

START TRANSACTION;

UPDATE cm_common_code
SET common_code_json = JSON_SET(
        common_code_json,
        '$.identifier_object_definitions.table.object_level', 3,
        '$.identifier_object_definitions.entity.object_level', 3,
        '$.identifier_object_definitions.attribute.object_level', 4,
        '$.identifier_object_definitions.erd.object_level', 2,
        '$.identifier_object_definitions.relationship.object_level', 3
    ),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = 'SYSTEM',
    client_ip = '127.0.0.1',
    program_id = 'REGISTER_REPOSITORY_IDENTIFIER_OBJECT_LEVELS_20260731'
WHERE group_code = 'ACTION_TYPE'
  AND code = 'REGISTER_REPOSITORY_OBJECT'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL;

SELECT
    group_code,
    code,
    JSON_EXTRACT(common_code_json, '$.identifier_object_definitions') AS identifier_object_definitions
FROM cm_common_code
WHERE group_code = 'ACTION_TYPE'
  AND code = 'REGISTER_REPOSITORY_OBJECT'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL;

COMMIT;
