-- Repository Domain Field Comment Patch 20260721
-- COMMENT-only maintenance. Data type, NULL, DEFAULT and indexes are preserved.

CREATE TABLE IF NOT EXISTS te_health_companion.at_audit_bkp_domain_comment_20260721
LIKE te_health_companion.at_audit;
INSERT INTO te_health_companion.at_audit_bkp_domain_comment_20260721
SELECT * FROM te_health_companion.at_audit
WHERE NOT EXISTS (SELECT 1 FROM te_health_companion.at_audit_bkp_domain_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_story_platform.sp_domain_bkp_domain_comment_20260721
LIKE te_story_platform.sp_domain;
INSERT INTO te_story_platform.sp_domain_bkp_domain_comment_20260721
SELECT * FROM te_story_platform.sp_domain
WHERE NOT EXISTS (SELECT 1 FROM te_story_platform.sp_domain_bkp_domain_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_story_platform.sp_entity_bkp_domain_comment_20260721
LIKE te_story_platform.sp_entity;
INSERT INTO te_story_platform.sp_entity_bkp_domain_comment_20260721
SELECT * FROM te_story_platform.sp_entity
WHERE NOT EXISTS (SELECT 1 FROM te_story_platform.sp_entity_bkp_domain_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_story_platform.sp_erd_bkp_domain_comment_20260721
LIKE te_story_platform.sp_erd;
INSERT INTO te_story_platform.sp_erd_bkp_domain_comment_20260721
SELECT * FROM te_story_platform.sp_erd
WHERE NOT EXISTS (SELECT 1 FROM te_story_platform.sp_erd_bkp_domain_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_story_platform.sp_object_bkp_domain_comment_20260721
LIKE te_story_platform.sp_object;
INSERT INTO te_story_platform.sp_object_bkp_domain_comment_20260721
SELECT * FROM te_story_platform.sp_object
WHERE NOT EXISTS (SELECT 1 FROM te_story_platform.sp_object_bkp_domain_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_common.cm_business_domain_bkp_domain_comment_20260721
LIKE te_common.cm_business_domain;
INSERT INTO te_common.cm_business_domain_bkp_domain_comment_20260721
SELECT * FROM te_common.cm_business_domain
WHERE NOT EXISTS (SELECT 1 FROM te_common.cm_business_domain_bkp_domain_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_common.cm_repository_bkp_domain_comment_20260721
LIKE te_common.cm_repository;
INSERT INTO te_common.cm_repository_bkp_domain_comment_20260721
SELECT * FROM te_common.cm_repository
WHERE NOT EXISTS (SELECT 1 FROM te_common.cm_repository_bkp_domain_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_common.cm_sequence_definition_bkp_domain_comment_20260721
LIKE te_common.cm_sequence_definition;
INSERT INTO te_common.cm_sequence_definition_bkp_domain_comment_20260721
SELECT * FROM te_common.cm_sequence_definition
WHERE NOT EXISTS (SELECT 1 FROM te_common.cm_sequence_definition_bkp_domain_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_common.cm_sequence_rule_bkp_domain_comment_20260721
LIKE te_common.cm_sequence_rule;
INSERT INTO te_common.cm_sequence_rule_bkp_domain_comment_20260721
SELECT * FROM te_common.cm_sequence_rule
WHERE NOT EXISTS (SELECT 1 FROM te_common.cm_sequence_rule_bkp_domain_comment_20260721 LIMIT 1);

ALTER TABLE te_health_companion.at_audit
MODIFY COLUMN business_domain_code varchar(99) DEFAULT NULL
COMMENT '감사 대상 업무 Domain Code. SSOT: te_common.cm_business_domain.business_domain_code. AC, AT, DC, EV, FB, RL, RP 등 공식 업무 Domain만 사용한다. Generator와 Engine은 Repository를 조회하며 값을 Hardcoding하지 않는다.';

ALTER TABLE te_story_platform.sp_domain
MODIFY COLUMN domain_code varchar(99) NOT NULL
COMMENT 'Story Programming 하위 Domain의 공식 Code이자 이 Master의 PK. SSOT: te_story_platform.sp_domain.domain_code. CO, RP, EN, WF, GN, MT 등 등록된 값만 사용하며 Table Prefix로 추론하지 않는다.',
MODIFY COLUMN business_code varchar(99) NOT NULL
COMMENT 'Domain이 소속된 공식 Business Code. SSOT: te_story_platform.sp_business.business_code. Domain 조회 시 business_code와 함께 해석한다.',
MODIFY COLUMN domain_name varchar(150) NOT NULL
COMMENT '공식 Domain 표시명. domain_code의 사람이 읽는 명칭이며 Identifier Code로 사용하지 않는다.',
MODIFY COLUMN domain_description varchar(2000) DEFAULT NULL
COMMENT '공식 Domain의 목적, 범위 및 사용 기준. Generator, Engine 및 AI가 Domain 의미를 해석하는 설명 원천이다.';

ALTER TABLE te_story_platform.sp_entity
MODIFY COLUMN business_code varchar(99) NOT NULL
COMMENT 'Entity 소속 Business Code. SSOT: te_story_platform.sp_business.business_code.',
MODIFY COLUMN domain_code varchar(99) NOT NULL
COMMENT 'Entity 소속 Story Platform Domain Code. SSOT: te_story_platform.sp_domain.domain_code. business_code에 속한 등록 Domain만 사용하고 Table Prefix나 이름으로 추론하지 않는다.';

ALTER TABLE te_story_platform.sp_erd
MODIFY COLUMN business_code varchar(99) NOT NULL
COMMENT 'ERD 소속 Business Code. SSOT: te_story_platform.sp_business.business_code.',
MODIFY COLUMN domain_code varchar(99) NOT NULL
COMMENT 'ERD 소속 Story Platform Domain Code. SSOT: te_story_platform.sp_domain.domain_code. business_code와 함께 Repository First로 해석한다.';

ALTER TABLE te_story_platform.sp_object
MODIFY COLUMN business_code varchar(99) NOT NULL
COMMENT 'Object 소속 공식 Business Code. SSOT: te_story_platform.sp_business.business_code. Level 4 Identifier의 Business Segment를 결정할 때 Repository에서 조회한다.',
MODIFY COLUMN domain_code varchar(99) NOT NULL
COMMENT 'Object 소속 공식 Story Platform Domain Code. SSOT: te_story_platform.sp_domain.domain_code. Level 4 Identifier의 Domain Segment를 결정하며 Table Prefix 기반 Hardcoding을 금지한다.';

ALTER TABLE te_common.cm_business_domain
MODIFY COLUMN business_domain_id varchar(99) NOT NULL
COMMENT '업무 Domain 정의의 Level 4 Identifier. 형식은 BUSINESS_DOMAIN_OBJECT_YYYYMMDD_HHMMSS_SEQ5를 따른다.',
MODIFY COLUMN business_domain_code varchar(99) NOT NULL
COMMENT '업무 Domain 공식 Code이자 Unique Business 분류 원천. AC, AT, DC, EV, FB, RL, RP 등 등록값만 사용하며 참조 컬럼은 이 Master를 SSOT로 사용한다.',
MODIFY COLUMN business_domain_name varchar(150) NOT NULL
COMMENT '업무 Domain 공식 표시명. business_domain_code의 사람이 읽는 명칭이며 Identifier Segment로 사용하지 않는다.';

ALTER TABLE te_common.cm_repository
MODIFY COLUMN business_code varchar(99) NOT NULL
COMMENT 'Repository Data의 공식 Business Code. 관련 Business Master 및 Repository Metadata에서 해석하며 값을 Hardcoding하지 않는다.',
MODIFY COLUMN domain_code varchar(99) NOT NULL
COMMENT 'Repository Data의 기능 Domain Code. SSOT: te_common.cm_common_code의 group_code=CM_DOMAIN. SE, AP, DB, DC, DU, EN, FG, IC, LM, MD, MN, RP, SC, ST, TP, TS 등 등록값만 사용한다.';

ALTER TABLE te_common.cm_sequence_definition
MODIFY COLUMN domain_code varchar(99) NOT NULL
COMMENT 'Sequence가 적용되는 공식 Platform Domain Code. SSOT: te_common.cm_common_code의 group_code=DOMAIN_CODE. CO, SP, HC, AI, SY, AD, MD 등 등록값만 사용한다.';

ALTER TABLE te_common.cm_sequence_rule
MODIFY COLUMN domain_code varchar(99) DEFAULT NULL
COMMENT 'Sequence Rule 적용 대상 공식 Platform Domain Code. SSOT: te_common.cm_common_code의 group_code=DOMAIN_CODE. CO, SP, HC, AI, SY, AD, MD 등 등록값만 사용하며 Prefix로 추론하지 않는다.';

SELECT table_schema, table_name, column_name, column_comment
FROM information_schema.columns
WHERE (table_schema, table_name, column_name) IN (
 ('te_health_companion','at_audit','business_domain_code'),
 ('te_story_platform','sp_domain','domain_code'),
 ('te_story_platform','sp_domain','business_code'),
 ('te_story_platform','sp_domain','domain_name'),
 ('te_story_platform','sp_domain','domain_description'),
 ('te_story_platform','sp_entity','business_code'),
 ('te_story_platform','sp_entity','domain_code'),
 ('te_story_platform','sp_erd','business_code'),
 ('te_story_platform','sp_erd','domain_code'),
 ('te_story_platform','sp_object','business_code'),
 ('te_story_platform','sp_object','domain_code'),
 ('te_common','cm_business_domain','business_domain_id'),
 ('te_common','cm_business_domain','business_domain_code'),
 ('te_common','cm_business_domain','business_domain_name'),
 ('te_common','cm_repository','business_code'),
 ('te_common','cm_repository','domain_code'),
 ('te_common','cm_sequence_definition','domain_code'),
 ('te_common','cm_sequence_rule','domain_code')
)
ORDER BY table_schema, table_name, ordinal_position;
