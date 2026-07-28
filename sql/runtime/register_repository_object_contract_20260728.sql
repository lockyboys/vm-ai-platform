-- Repository Object Rule common-code contract
-- Rule selects ACTION_TYPE; common_code_json supplies Identifier/Object/Entity codes.

INSERT INTO cm_common_code_group
(group_code, group_name, group_description, sort_no, status_code, reserved_yn,
 system_yn, created_by, updated_by, client_ip, program_id, lifecycle_status_code)
VALUES
('ENTITY_TYPE', 'Entity Type', '논리·물리 Entity 구분 공통코드', 63, 'ACTIVE', 'Y',
 'Y', 'SYSTEM', 'SYSTEM', '127.0.0.1',
 'REGISTER_REPOSITORY_OBJECT_CONTRACT_20260728', 'CREATE_MAINTAIN')
ON DUPLICATE KEY UPDATE
    group_name = VALUES(group_name),
    group_description = VALUES(group_description),
    status_code = 'ACTIVE',
    system_yn = 'Y',
    deleted_by = NULL,
    deleted_dt = NULL,
    updated_by = VALUES(updated_by),
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id);

INSERT INTO cm_common_code
(group_code, code, code_name, common_code_description, sort_no, status_code,
 created_by, updated_by, client_ip, program_id, common_code_json,
 lifecycle_status_code)
VALUES
('ENTITY_TYPE', 'LOGICAL', '논리 Entity', 'Table Object의 논리 테이블 정의', 10,
 'ACTIVE', 'SYSTEM', 'SYSTEM', '127.0.0.1',
 'REGISTER_REPOSITORY_OBJECT_CONTRACT_20260728', NULL, 'CREATE_MAINTAIN'),
('ENTITY_TYPE', 'PHYSICAL', '물리 Entity', 'Table Object의 물리 테이블 정의', 20,
 'ACTIVE', 'SYSTEM', 'SYSTEM', '127.0.0.1',
 'REGISTER_REPOSITORY_OBJECT_CONTRACT_20260728', NULL, 'CREATE_MAINTAIN')
ON DUPLICATE KEY UPDATE
    code_name = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    status_code = 'ACTIVE',
    deleted_by = NULL,
    deleted_dt = NULL,
    updated_by = VALUES(updated_by),
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id);

UPDATE cm_common_code
SET common_code_json = JSON_OBJECT(
        'identifier_object_codes', JSON_OBJECT(
            'table', 'TABLE',
            'entity', 'ENTITY',
            'attribute', 'ATTRIBUTE',
            'erd', 'ERD',
            'relationship', 'RELATIONSHIP'
        ),
        'identifier_object_definitions', JSON_OBJECT(
            'table', JSON_OBJECT(
                'object_name', 'Table Object',
                'object_description', 'Database Table Object Identifier 발급 기준.',
                'identifier_target_code', 'OB'
            ),
            'entity', JSON_OBJECT(
                'object_name', 'Entity Object',
                'object_description', 'Logical and Physical Entity Identifier 발급 기준.',
                'identifier_target_code', 'EN'
            ),
            'attribute', JSON_OBJECT(
                'object_name', 'Attribute Object',
                'object_description', 'Entity Attribute Identifier 발급 기준.',
                'identifier_target_code', 'AT'
            ),
            'erd', JSON_OBJECT(
                'object_name', 'ERD Object',
                'object_description', 'Entity Relationship Diagram Identifier 발급 기준.',
                'identifier_target_code', 'OB'
            ),
            'relationship', JSON_OBJECT(
                'object_name', 'Relationship Object',
                'object_description', 'Entity Relationship Identifier 발급 기준.',
                'identifier_target_code', 'RE'
            )
        ),
        'object_definition_business_code', 'SP',
        'object_definition_domain_code', 'RP',
        'object_type_code', 'TABLE',
        'object_level', 3,
        'sequence_scope_code', 'DAILY',
        'sequence_length', 5,
        'entity_type_group_code', 'ENTITY_TYPE',
        'logical_entity_type_code', 'LOGICAL',
        'physical_entity_type_code', 'PHYSICAL'
    ),
    updated_by = 'SYSTEM',
    client_ip = '127.0.0.1',
    program_id = 'REGISTER_REPOSITORY_OBJECT_CONTRACT_20260728'
WHERE group_code = 'ACTION_TYPE'
  AND code = 'REGISTER_REPOSITORY_OBJECT'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL;

SELECT group_code, code, code_name, common_code_json
FROM cm_common_code
WHERE (group_code = 'ACTION_TYPE' AND code = 'REGISTER_REPOSITORY_OBJECT')
   OR group_code = 'ENTITY_TYPE'
ORDER BY group_code, sort_no, code;
