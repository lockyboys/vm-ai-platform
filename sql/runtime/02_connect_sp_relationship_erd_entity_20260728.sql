-- File Story
-- ERD Relationship가 동일 ERD의 Source/Target Entity 배치를 참조하도록 보장한다.
--
-- Change History
-- 20260728 | SYSTEM | sp_relationship에 ERD 범위 Entity 복합 FK 연결
-- 20260728 | SYSTEM | 전체 ERD 참조 검증과 재실행 보호 조건 추가

DELIMITER $$

DROP PROCEDURE IF EXISTS connect_sp_relationship_erd_entity_20260728$$
CREATE PROCEDURE connect_sp_relationship_erd_entity_20260728()
BEGIN
    DECLARE orphan_count INT DEFAULT 0;
    DECLARE invalid_erd_count INT DEFAULT 0;

    SELECT COUNT(*)
      INTO invalid_erd_count
      FROM sp_relationship relationship_row
      LEFT JOIN sp_erd erd_row
        ON erd_row.erd_id = relationship_row.erd_id
     WHERE relationship_row.erd_id IS NOT NULL
       AND erd_row.erd_id IS NULL;

    IF invalid_erd_count > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'sp_relationship contains an erd_id not registered in sp_erd.';
    END IF;

    SELECT COUNT(*)
      INTO orphan_count
      FROM sp_relationship relationship_row
      LEFT JOIN sp_entity source_entity
        ON source_entity.erd_id = relationship_row.erd_id
       AND source_entity.entity_id = relationship_row.source_entity_id
      LEFT JOIN sp_entity target_entity
        ON target_entity.erd_id = relationship_row.erd_id
       AND target_entity.entity_id = relationship_row.target_entity_id
     WHERE relationship_row.relationship_scope_code = 'ERD'
       AND relationship_row.deleted_dt IS NULL
       AND (source_entity.entity_id IS NULL OR target_entity.entity_id IS NULL);

    IF orphan_count > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Run business_domain_repository_sync_batch before adding ERD Entity foreign keys.';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
         WHERE table_schema = DATABASE() AND table_name = 'sp_relationship'
           AND index_name = 'ix_sp_relationship_source_erd_entity'
    ) THEN
        ALTER TABLE sp_relationship
            ADD KEY ix_sp_relationship_source_erd_entity
                (erd_id, source_entity_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
         WHERE table_schema = DATABASE() AND table_name = 'sp_relationship'
           AND index_name = 'ix_sp_relationship_target_erd_entity'
    ) THEN
        ALTER TABLE sp_relationship
            ADD KEY ix_sp_relationship_target_erd_entity
                (erd_id, target_entity_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
         WHERE constraint_schema = DATABASE() AND table_name = 'sp_relationship'
           AND constraint_name = 'fk_sp_relationship_erd'
           AND constraint_type = 'FOREIGN KEY'
    ) THEN
        ALTER TABLE sp_relationship
            ADD CONSTRAINT fk_sp_relationship_erd
                FOREIGN KEY (erd_id) REFERENCES sp_erd (erd_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
         WHERE constraint_schema = DATABASE() AND table_name = 'sp_relationship'
           AND constraint_name = 'fk_sp_relationship_source_entity'
           AND constraint_type = 'FOREIGN KEY'
    ) THEN
        ALTER TABLE sp_relationship
            ADD CONSTRAINT fk_sp_relationship_source_entity
                FOREIGN KEY (erd_id, source_entity_id)
                REFERENCES sp_entity (erd_id, entity_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
         WHERE constraint_schema = DATABASE() AND table_name = 'sp_relationship'
           AND constraint_name = 'fk_sp_relationship_target_entity'
           AND constraint_type = 'FOREIGN KEY'
    ) THEN
        ALTER TABLE sp_relationship
            ADD CONSTRAINT fk_sp_relationship_target_entity
                FOREIGN KEY (erd_id, target_entity_id)
                REFERENCES sp_entity (erd_id, entity_id);
    END IF;
END$$

CALL connect_sp_relationship_erd_entity_20260728()$$
DROP PROCEDURE connect_sp_relationship_erd_entity_20260728$$

DELIMITER ;

SELECT relationship_row.erd_id,
       COUNT(*) AS relationship_count
FROM sp_relationship relationship_row
WHERE relationship_row.relationship_scope_code = 'ERD'
  AND relationship_row.deleted_dt IS NULL
GROUP BY relationship_row.erd_id
ORDER BY relationship_row.erd_id;
