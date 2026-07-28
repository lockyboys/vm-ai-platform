-- sp_entity/sp_attribute Table Object linkage and bilingual attribute names.
-- Precondition: both tables are empty or existing rows have been migrated first.

ALTER TABLE sp_entity
    ADD COLUMN object_id VARCHAR(99) NOT NULL
        COMMENT 'Table Object ID. sp_object.object_id를 참조하며 논리·물리 Entity가 동일 값을 공유한다.'
        AFTER entity_id,
    ADD KEY ix_sp_entity_object (object_id),
    ADD UNIQUE KEY uk_sp_entity_object_type (object_id, entity_type_code),
    ADD CONSTRAINT fk_sp_entity_object
        FOREIGN KEY (object_id) REFERENCES sp_object (object_id);

ALTER TABLE sp_attribute
    ADD COLUMN object_id VARCHAR(99) NOT NULL
        COMMENT 'Table Object ID. 논리·물리 Entity와 동일한 Table Object 범위를 공유한다.'
        AFTER attribute_id,
    ADD COLUMN attribute_name_ko VARCHAR(150) NOT NULL
        COMMENT '업무·화면·문서에서 사용하는 Attribute 한글명.'
        AFTER attribute_name,
    ADD COLUMN attribute_name_en VARCHAR(150) NOT NULL
        COMMENT '표준 영문 Attribute 명칭.'
        AFTER attribute_name_ko,
    ADD COLUMN column_name VARCHAR(150) NOT NULL
        COMMENT '실제 물리 Database Column 명.'
        AFTER attribute_name_en,
    ADD KEY ix_sp_attribute_object (object_id),
    ADD UNIQUE KEY uk_sp_attribute_object_column (object_id, column_name),
    ADD CONSTRAINT fk_sp_attribute_object
        FOREIGN KEY (object_id) REFERENCES sp_object (object_id);

SELECT table_name, column_name, column_type, is_nullable, column_comment
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name IN ('sp_entity', 'sp_attribute')
ORDER BY table_name, ordinal_position;
