-- SPS Common Code full lifecycle classification and normalization batch
-- Scope: current 62 groups / 415 codes plus lifecycle metadata codes
-- No physical deletion. Invalid PK code values are classified MODIFY, not renamed.
USE te_common;

SET @actor='SYSTEM';
SET @client_ip='127.0.0.1';
SET @program_id='CM_COMMON_CODE_LIFECYCLE_BATCH_20260722';
SET @batch_dt=NOW();

-- DDL is intentionally idempotent. MariaDB DDL commits independently.
ALTER TABLE cm_common_code_group
  ADD COLUMN IF NOT EXISTS lifecycle_status_code VARCHAR(99) NOT NULL DEFAULT 'CREATE_MAINTAIN'
  COMMENT '공통코드 Group의 Repository 생명주기 판정 상태. SSOT: COMMON_CODE_LIFECYCLE_STATUS.';
ALTER TABLE cm_common_code
  ADD COLUMN IF NOT EXISTS lifecycle_status_code VARCHAR(99) NOT NULL DEFAULT 'CREATE_MAINTAIN'
  COMMENT '공통코드 Object의 Repository 생명주기 판정 상태. SSOT: COMMON_CODE_LIFECYCLE_STATUS.';

START TRANSACTION;

INSERT INTO cm_common_code_group
(group_code,group_name,group_description,sort_no,status_code,reserved_yn,system_yn,
 created_by,updated_by,client_ip,program_id,lifecycle_status_code)
VALUES
('COMMON_CODE_LIFECYCLE_STATUS','공통코드 생명주기 판정 상태',
 '공통코드 Object의 생성·유지, 수정, 폐기 후보, 폐기 진행, 폐기, 보존 판정을 관리한다.',
 340,'ACTIVE','Y','Y',@actor,@actor,@client_ip,@program_id,'CREATE_MAINTAIN')
ON DUPLICATE KEY UPDATE
 group_name=VALUES(group_name),group_description=VALUES(group_description),
 status_code='ACTIVE',reserved_yn='Y',system_yn='Y',updated_by=@actor,
 client_ip=@client_ip,program_id=@program_id,lifecycle_status_code='CREATE_MAINTAIN';

INSERT INTO cm_common_code
(group_code,code,code_name,common_code_description,sort_no,status_code,
 created_by,updated_by,client_ip,program_id,common_code_json,lifecycle_status_code)
VALUES
('COMMON_CODE_LIFECYCLE_STATUS','CREATE_MAINTAIN','생성/유지','신규 생성되었거나 현재 정상 사용 중인 공통코드 Object.',10,'ACTIVE',@actor,@actor,@client_ip,@program_id,JSON_OBJECT('terminal_yn','N'),'CREATE_MAINTAIN'),
('COMMON_CODE_LIFECYCLE_STATUS','MODIFY','수정','설명, 명칭, 정렬, program_id 또는 Repository 연결 보완이 필요한 공통코드 Object.',20,'ACTIVE',@actor,@actor,@client_ip,@program_id,JSON_OBJECT('terminal_yn','N'),'CREATE_MAINTAIN'),
('COMMON_CODE_LIFECYCLE_STATUS','DISPOSAL_CANDIDATE','폐기 후보','미사용 가능성이 있어 참조 및 영향도 분석이 필요한 공통코드 Object.',30,'ACTIVE',@actor,@actor,@client_ip,@program_id,JSON_OBJECT('terminal_yn','N','requires_impact_analysis_yn','Y'),'CREATE_MAINTAIN'),
('COMMON_CODE_LIFECYCLE_STATUS','DISPOSAL_IN_PROGRESS','폐기 진행','폐기 결정 후 대체 및 참조 해제 절차가 진행 중인 공통코드 Object.',40,'ACTIVE',@actor,@actor,@client_ip,@program_id,JSON_OBJECT('terminal_yn','N','new_use_allowed_yn','N'),'CREATE_MAINTAIN'),
('COMMON_CODE_LIFECYCLE_STATUS','DISPOSED','폐기','논리적 폐기가 완료되어 신규 사용이 차단된 공통코드 Object.',50,'ACTIVE',@actor,@actor,@client_ip,@program_id,JSON_OBJECT('terminal_yn','Y','new_use_allowed_yn','N'),'CREATE_MAINTAIN'),
('COMMON_CODE_LIFECYCLE_STATUS','PRESERVE','보존','이력, 감사 및 Evidence 목적으로 유지하며 물리 삭제하지 않는 공통코드 Object.',60,'ACTIVE',@actor,@actor,@client_ip,@program_id,JSON_OBJECT('terminal_yn','Y','physical_delete_allowed_yn','N'),'CREATE_MAINTAIN')
ON DUPLICATE KEY UPDATE
 code_name=VALUES(code_name),common_code_description=VALUES(common_code_description),
 sort_no=VALUES(sort_no),status_code='ACTIVE',updated_by=@actor,client_ip=@client_ip,
 program_id=@program_id,common_code_json=VALUES(common_code_json),
 lifecycle_status_code='CREATE_MAINTAIN';

DROP TEMPORARY TABLE IF EXISTS tmp_issue_group;
CREATE TEMPORARY TABLE tmp_issue_group AS
SELECT g.group_code
FROM cm_common_code_group g
WHERE g.group_code <> 'COMMON_CODE_LIFECYCLE_STATUS'
  AND (
    NULLIF(TRIM(g.group_description),'') IS NULL OR
    NULLIF(TRIM(g.program_id),'') IS NULL OR
    EXISTS (
      SELECT 1 FROM cm_common_code c
      WHERE c.group_code=g.group_code
      GROUP BY c.sort_no HAVING COUNT(*)>1
    ) OR
    EXISTS (
      SELECT 1 FROM cm_common_code c
      WHERE c.group_code=g.group_code
        AND (NULLIF(TRIM(c.common_code_description),'') IS NULL
          OR NULLIF(TRIM(c.program_id),'') IS NULL
          OR c.code NOT REGEXP '^[A-Z][A-Z0-9_]*$')
    )
  );

DROP TEMPORARY TABLE IF EXISTS tmp_issue_code;
CREATE TEMPORARY TABLE tmp_issue_code AS
SELECT c.group_code,c.code
FROM cm_common_code c
WHERE c.group_code <> 'COMMON_CODE_LIFECYCLE_STATUS'
  AND (
    NULLIF(TRIM(c.common_code_description),'') IS NULL OR
    NULLIF(TRIM(c.program_id),'') IS NULL OR
    c.code NOT REGEXP '^[A-Z][A-Z0-9_]*$' OR
    EXISTS (
      SELECT 1 FROM cm_common_code x
      WHERE x.group_code=c.group_code AND x.sort_no=c.sort_no
      GROUP BY x.group_code,x.sort_no HAVING COUNT(*)>1
    )
  );

UPDATE cm_common_code_group g
SET g.lifecycle_status_code =
  CASE
    WHEN g.status_code='RETIRED' THEN 'PRESERVE'
    WHEN EXISTS (SELECT 1 FROM tmp_issue_group i WHERE i.group_code=g.group_code) THEN 'MODIFY'
    ELSE 'CREATE_MAINTAIN'
  END,
  g.updated_by=@actor,g.client_ip=@client_ip,
  g.program_id=COALESCE(NULLIF(TRIM(g.program_id),''),@program_id);

UPDATE cm_common_code c
SET c.lifecycle_status_code =
  CASE
    WHEN c.status_code='RETIRED' THEN 'PRESERVE'
    WHEN EXISTS (SELECT 1 FROM tmp_issue_code i WHERE i.group_code=c.group_code AND i.code=c.code) THEN 'MODIFY'
    ELSE 'CREATE_MAINTAIN'
  END,
  c.updated_by=@actor,c.client_ip=@client_ip,
  c.program_id=COALESCE(NULLIF(TRIM(c.program_id),''),@program_id);

-- Missing descriptions are repaired from the actual Object names.
UPDATE cm_common_code_group
SET group_description=CONCAT(group_name,' 공통코드 Group의 공식 값, 의미, 정렬 및 생명주기를 관리한다.'),
    updated_by=@actor,client_ip=@client_ip,program_id=@program_id
WHERE NULLIF(TRIM(group_description),'') IS NULL;

UPDATE cm_common_code
SET common_code_description=CONCAT(code_name,' 공통코드 값의 의미와 Repository 사용 기준을 관리한다.'),
    updated_by=@actor,client_ip=@client_ip,program_id=@program_id
WHERE NULLIF(TRIM(common_code_description),'') IS NULL;

-- Resolve duplicate sort_no deterministically within affected groups.
DROP TEMPORARY TABLE IF EXISTS tmp_duplicate_sort_group;
CREATE TEMPORARY TABLE tmp_duplicate_sort_group AS
SELECT DISTINCT group_code
FROM cm_common_code
GROUP BY group_code,sort_no
HAVING COUNT(*)>1;

DROP TEMPORARY TABLE IF EXISTS tmp_sort_resequence;
CREATE TEMPORARY TABLE tmp_sort_resequence AS
SELECT c.group_code,c.code,
       ROW_NUMBER() OVER(PARTITION BY c.group_code ORDER BY c.sort_no,c.code)*10 AS new_sort_no
FROM cm_common_code c
JOIN tmp_duplicate_sort_group d ON d.group_code=c.group_code;

UPDATE cm_common_code c
JOIN tmp_sort_resequence r ON r.group_code=c.group_code AND r.code=c.code
SET c.sort_no=r.new_sort_no,c.updated_by=@actor,c.client_ip=@client_ip,c.program_id=@program_id;

-- Immutable History: one row for every classified Group and Code.
INSERT IGNORE INTO cm_change_history
(change_history_id,target_database_name,target_table_name,target_record_id,action_type,
 change_story,created_by,created_dt,client_ip,program_id,status_code)
SELECT CONCAT('CM_CO_LC_G_',DATE_FORMAT(@batch_dt,'%Y%m%d%H%i%s'),'_',LPAD(ROW_NUMBER() OVER(ORDER BY group_code),3,'0')),
       'te_common','cm_common_code_group',group_code,'BATCH',
       CONCAT(group_code,' Group을 ',lifecycle_status_code,' 상태로 판정하고 Repository Metadata를 보완한다.'),
       @actor,@batch_dt,@client_ip,@program_id,'ACTIVE'
FROM cm_common_code_group;

INSERT IGNORE INTO cm_change_history
(change_history_id,target_database_name,target_table_name,target_record_id,action_type,
 change_story,created_by,created_dt,client_ip,program_id,status_code)
SELECT CONCAT('CM_CO_LC_C_',DATE_FORMAT(@batch_dt,'%Y%m%d%H%i%s'),'_',LPAD(ROW_NUMBER() OVER(ORDER BY group_code,code),3,'0')),
       'te_common','cm_common_code',CONCAT(group_code,':',code),'BATCH',
       CONCAT(group_code,'.',code,' Code를 ',lifecycle_status_code,' 상태로 판정하고 Repository Metadata를 보완한다.'),
       @actor,@batch_dt,@client_ip,@program_id,'ACTIVE'
FROM cm_common_code;

-- Assertions: no missing classifications/descriptions/program_id or duplicate sort_no.
SET @bad_group=(SELECT COUNT(*) FROM cm_common_code_group
 WHERE lifecycle_status_code NOT IN ('CREATE_MAINTAIN','MODIFY','DISPOSAL_CANDIDATE','DISPOSAL_IN_PROGRESS','DISPOSED','PRESERVE')
    OR NULLIF(TRIM(group_description),'') IS NULL OR NULLIF(TRIM(program_id),'') IS NULL);
SET @bad_code=(SELECT COUNT(*) FROM cm_common_code
 WHERE lifecycle_status_code NOT IN ('CREATE_MAINTAIN','MODIFY','DISPOSAL_CANDIDATE','DISPOSAL_IN_PROGRESS','DISPOSED','PRESERVE')
    OR NULLIF(TRIM(common_code_description),'') IS NULL OR NULLIF(TRIM(program_id),'') IS NULL);
SET @duplicate_sort=(SELECT COUNT(*) FROM (
 SELECT group_code,sort_no FROM cm_common_code GROUP BY group_code,sort_no HAVING COUNT(*)>1
) q);

DROP TEMPORARY TABLE IF EXISTS tmp_assert;
CREATE TEMPORARY TABLE tmp_assert
(validation_result TINYINT NOT NULL,CONSTRAINT chk_common_code_lifecycle_assert CHECK(validation_result=1));
INSERT INTO tmp_assert VALUES(IF(@bad_group=0 AND @bad_code=0 AND @duplicate_sort=0,1,0));
DROP TEMPORARY TABLE tmp_assert;

COMMIT;

SELECT lifecycle_status_code,COUNT(*) group_count
FROM cm_common_code_group GROUP BY lifecycle_status_code ORDER BY lifecycle_status_code;
SELECT lifecycle_status_code,COUNT(*) code_count
FROM cm_common_code GROUP BY lifecycle_status_code ORDER BY lifecycle_status_code;
SELECT @bad_group bad_group,@bad_code bad_code,@duplicate_sort duplicate_sort;
SELECT group_code,group_name,group_description,sort_no,status_code,lifecycle_status_code,program_id
FROM cm_common_code_group ORDER BY sort_no,group_code;
SELECT group_code,code,code_name,common_code_description,sort_no,status_code,lifecycle_status_code,program_id
FROM cm_common_code ORDER BY group_code,sort_no,code;
