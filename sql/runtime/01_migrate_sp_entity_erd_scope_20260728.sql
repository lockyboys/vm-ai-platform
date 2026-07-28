-- File Story
-- sp_entity를 ERD별 Entity 배치 Repository로 안전하게 이관한다.
--
-- Change History
-- 20260728 | SYSTEM | sp_entity에 erd_id를 연결하고 ERD 범위 복합키로 변경
-- 20260728 | SYSTEM | 부분 실행과 재실행을 허용하도록 Schema Metadata 기반 보호 조건 추가

DELIMITER $$

DROP PROCEDURE IF EXISTS migrate_sp_entity_erd_scope_20260728$$
CREATE PROCEDURE migrate_sp_entity_erd_scope_20260728()
BEGIN
    DECLARE invalid_mapping_count INT DEFAULT 0;
    DECLARE erd_column_count INT DEFAULT 0;
    DECLARE primary_key_is_target INT DEFAULT 0;

    SELECT COUNT(*)
      INTO invalid_mapping_count
      FROM sp_entity entity_row
     WHERE (
         SELECT COUNT(*)
           FROM sp_erd erd_row
          WHERE erd_row.business_code = entity_row.business_code
            AND erd_row.domain_code = entity_row.domain_code
            AND erd_row.enabled_yn = 'Y'
            AND erd_row.deleted_dt IS NULL
     ) <> 1;

    IF invalid_mapping_count > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'sp_entity ERD mapping must resolve to exactly one active sp_erd row.';
    END IF;

    SELECT COUNT(*)
      INTO erd_column_count
      FROM information_schema.columns
     WHERE table_schema = DATABASE()
       AND table_name = 'sp_entity'
       AND column_name = 'erd_id';

    IF erd_column_count = 0 THEN
        ALTER TABLE sp_entity
            ADD COLUMN erd_id VARCHAR(99) NULL
                COMMENT 'ERD ID. Entity가 배치되는 ERD Object를 식별한다.'
                AFTER entity_id;
    END IF;

    UPDATE sp_entity entity_row
    JOIN sp_erd erd_row
      ON erd_row.business_code = entity_row.business_code
     AND erd_row.domain_code = entity_row.domain_code
     AND erd_row.enabled_yn = 'Y'
     AND erd_row.deleted_dt IS NULL
       SET entity_row.erd_id = erd_row.erd_id
     WHERE entity_row.erd_id IS NULL;

    IF EXISTS (
        SELECT 1
          FROM sp_entity
         WHERE erd_id IS NULL
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'sp_entity.erd_id contains NULL after migration mapping.';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM information_schema.statistics
         WHERE table_schema = DATABASE()
           AND table_name = 'sp_entity'
           AND index_name = 'uk_sp_table_definition_01'
    ) THEN
        ALTER TABLE sp_entity DROP INDEX uk_sp_table_definition_01;
    END IF;

    IF EXISTS (
        SELECT 1
          FROM information_schema.statistics
         WHERE table_schema = DATABASE()
           AND table_name = 'sp_entity'
           AND index_name = 'uk_sp_entity_object_type'
    ) THEN
        ALTER TABLE sp_entity DROP INDEX uk_sp_entity_object_type;
    END IF;

    SELECT COUNT(*)
      INTO primary_key_is_target
      FROM (
          SELECT GROUP_CONCAT(column_name ORDER BY seq_in_index) AS key_columns
            FROM information_schema.statistics
           WHERE table_schema = DATABASE()
             AND table_name = 'sp_entity'
             AND index_name = 'PRIMARY'
      ) primary_key_metadata
     WHERE primary_key_metadata.key_columns = 'erd_id,entity_id';

    IF primary_key_is_target = 0 THEN
        ALTER TABLE sp_entity
            DROP PRIMARY KEY,
            MODIFY COLUMN erd_id VARCHAR(99) NOT NULL
                COMMENT 'ERD ID. Entity가 배치되는 ERD Object를 식별한다.',
            ADD PRIMARY KEY (erd_id, entity_id);
    ELSE
        ALTER TABLE sp_entity
            MODIFY COLUMN erd_id VARCHAR(99) NOT NULL
                COMMENT 'ERD ID. Entity가 배치되는 ERD Object를 식별한다.';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
         WHERE table_schema = DATABASE() AND table_name = 'sp_entity'
           AND index_name = 'uk_sp_entity_erd_name'
    ) THEN
        ALTER TABLE sp_entity
            ADD UNIQUE KEY uk_sp_entity_erd_name (erd_id, entity_name);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
         WHERE table_schema = DATABASE() AND table_name = 'sp_entity'
           AND index_name = 'uk_sp_entity_erd_object_type'
    ) THEN
        ALTER TABLE sp_entity
            ADD UNIQUE KEY uk_sp_entity_erd_object_type
                (erd_id, object_id, entity_type_code);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
         WHERE table_schema = DATABASE() AND table_name = 'sp_entity'
           AND index_name = 'ix_sp_entity_id'
    ) THEN
        ALTER TABLE sp_entity ADD KEY ix_sp_entity_id (entity_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
         WHERE constraint_schema = DATABASE() AND table_name = 'sp_entity'
           AND constraint_name = 'fk_sp_entity_erd'
           AND constraint_type = 'FOREIGN KEY'
    ) THEN
        ALTER TABLE sp_entity
            ADD CONSTRAINT fk_sp_entity_erd
                FOREIGN KEY (erd_id) REFERENCES sp_erd (erd_id);
    END IF;
END$$

CALL migrate_sp_entity_erd_scope_20260728()$$
DROP PROCEDURE migrate_sp_entity_erd_scope_20260728$$

DELIMITER ;

SELECT erd_id, entity_type_code, COUNT(*) AS entity_count
FROM sp_entity
GROUP BY erd_id, entity_type_code
ORDER BY erd_id, entity_type_code;
