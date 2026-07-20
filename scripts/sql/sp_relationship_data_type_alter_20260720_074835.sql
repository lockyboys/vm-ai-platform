-- sp_relationship Data Type Metadata Standardization
-- Generated: 2026-07-20 KST
-- Target database role: STORY_PLATFORM
-- Target table: sp_relationship
-- Verified live rows: 4
-- Verified foreign keys: 0
-- Verified shrink maxima:
--   relationship_id      max 40 -> VARCHAR(99)
--   source_object_id     max 18 -> VARCHAR(99)
--   target_object_id     max 28 -> VARCHAR(99)
--   relationship_code    max 44 -> VARCHAR(99)
--   program_id           max 21 -> VARCHAR(99)

-- 1. Pre-change evidence
SELECT
    column_name,
    column_type,
    is_nullable,
    column_default,
    column_key,
    extra,
    column_comment
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'sp_relationship'
ORDER BY ordinal_position;

-- 2. Physical Data Type change
ALTER TABLE sp_relationship
    MODIFY COLUMN relationship_id VARCHAR(99) NOT NULL
        COMMENT 'Relationship Object ID. Identifier Engine이 생성한 Level 3 정식 식별자',
    MODIFY COLUMN relationship_scope_code VARCHAR(99) NOT NULL DEFAULT 'ERD'
        COMMENT 'Relationship Scope Code. ERD 또는 OBJECT',
    MODIFY COLUMN erd_id VARCHAR(99) DEFAULT NULL
        COMMENT 'ERD Scope에서 사용하는 ERD ID',
    MODIFY COLUMN source_entity_id VARCHAR(99) DEFAULT NULL
        COMMENT 'ERD Scope에서 사용하는 Source Entity ID',
    MODIFY COLUMN source_object_id VARCHAR(99) DEFAULT NULL
        COMMENT 'OBJECT Scope에서 사용하는 Source Object 식별자',
    MODIFY COLUMN source_object_type_code VARCHAR(99) DEFAULT NULL
        COMMENT 'Source Object 유형 코드. KNOWLEDGE, LIFECYCLE, RULE, VERIFIED_SQL 등',
    MODIFY COLUMN target_entity_id VARCHAR(99) DEFAULT NULL
        COMMENT 'ERD Scope에서 사용하는 Target Entity ID',
    MODIFY COLUMN target_object_id VARCHAR(99) DEFAULT NULL
        COMMENT 'OBJECT Scope에서 사용하는 Target Object 식별자',
    MODIFY COLUMN target_object_type_code VARCHAR(99) DEFAULT NULL
        COMMENT 'Target Object 유형 코드. KNOWLEDGE, LIFECYCLE, RULE, VERIFIED_SQL 등',
    MODIFY COLUMN relationship_code VARCHAR(99) NOT NULL
        COMMENT 'Relationship Code. 사람이 이해하고 Generator가 참조할 수 있는 Relationship의 의미 기반 식별 코드로 사용한다.',
    MODIFY COLUMN relationship_type_code VARCHAR(99) NOT NULL DEFAULT 'FK'
        COMMENT 'Relationship Type Code. Relationship의 유형을 식별하고 Engine과 Generator의 처리 방식을 결정하기 위해 사용한다.',
    MODIFY COLUMN delete_rule_code VARCHAR(99) DEFAULT NULL
        COMMENT 'Delete Rule Code. Target 또는 Source 삭제 시 Relationship 처리 규칙을 정의하여 Database FK와 Generator 생성 기준으로 사용한다.',
    MODIFY COLUMN update_rule_code VARCHAR(99) DEFAULT NULL
        COMMENT 'Update Rule Code. Target 또는 Source 변경 시 Relationship 처리 규칙을 정의하여 Database FK와 Generator 생성 기준으로 사용한다.',
    MODIFY COLUMN created_by VARCHAR(99) NOT NULL DEFAULT 'SYSTEM'
        COMMENT 'Created By. Relationship을 최초 생성한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN updated_by VARCHAR(99) DEFAULT NULL
        COMMENT 'Updated By. Relationship을 마지막으로 수정한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN deleted_by VARCHAR(99) DEFAULT NULL
        COMMENT 'Deleted By. Relationship을 삭제 처리한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN client_ip VARCHAR(99) DEFAULT NULL
        COMMENT 'Client IP. Relationship 변경 요청이 발생한 클라이언트 IP를 추적하기 위해 사용한다.',
    MODIFY COLUMN program_id VARCHAR(99) DEFAULT NULL
        COMMENT 'Program ID. Relationship 변경을 수행한 프로그램 또는 Generator를 추적하기 위해 사용한다.';

-- 3. Post-change verification
SELECT
    column_name,
    column_type,
    is_nullable,
    column_default,
    column_key,
    extra,
    column_comment
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'sp_relationship'
  AND column_name IN (
      'relationship_id',
      'relationship_scope_code',
      'erd_id',
      'source_entity_id',
      'source_object_id',
      'source_object_type_code',
      'target_entity_id',
      'target_object_id',
      'target_object_type_code',
      'relationship_code',
      'relationship_type_code',
      'delete_rule_code',
      'update_rule_code',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS relationship_row_count
FROM sp_relationship;
