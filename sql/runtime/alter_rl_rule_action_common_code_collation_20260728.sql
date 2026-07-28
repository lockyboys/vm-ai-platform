-- rl_rule_action ACTION_TYPE 공통코드 참조 Collation 정비
-- cm_common_code.code와 동일한 utf8mb4_unicode_ci를 적용하여 코드 비교 오류를 제거한다.

ALTER TABLE rl_rule_action
    MODIFY COLUMN action_type_code VARCHAR(99)
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci
    NOT NULL
    COMMENT 'Rule Action 수행 유형 코드. SSOT: te_common.cm_common_code의 group_code=ACTION_TYPE. SAFE_MODE_ON, HOSPITAL_RECOMMEND, HUMAN_REVIEW 등 등록된 Code만 사용하며 Hardcoding하지 않는다.';

SELECT column_name,
       character_set_name,
       collation_name
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'rl_rule_action'
  AND column_name = 'action_type_code';
