-- SPS Common Code complete census final reclassification batch
-- Scope: 63 groups / 421 codes
-- Basis: complete row audit; LANGUAGE uses ISO 639-1 and LOCALE uses BCP 47.
-- No physical deletion. Evidence-based terminal lifecycle states are preserved.
USE te_common;

SET @actor='SYSTEM';
SET @client_ip='127.0.0.1';
SET @program_id='CM_COMMON_CODE_FINAL_RECLASSIFICATION_20260722';
SET @batch_dt=NOW();

START TRANSACTION;

DROP TEMPORARY TABLE IF EXISTS tmp_group_lifecycle_change;
CREATE TEMPORARY TABLE tmp_group_lifecycle_change AS
SELECT
    group_code,
    lifecycle_status_code AS before_status_code,
    'CREATE_MAINTAIN' AS after_status_code
FROM cm_common_code_group
WHERE lifecycle_status_code='MODIFY';

DROP TEMPORARY TABLE IF EXISTS tmp_code_lifecycle_change;
CREATE TEMPORARY TABLE tmp_code_lifecycle_change AS
SELECT
    group_code,
    code,
    lifecycle_status_code AS before_status_code,
    'CREATE_MAINTAIN' AS after_status_code
FROM cm_common_code
WHERE lifecycle_status_code='MODIFY';

SET @group_change_count=(SELECT COUNT(*) FROM tmp_group_lifecycle_change);
SET @code_change_count=(SELECT COUNT(*) FROM tmp_code_lifecycle_change);

DROP TEMPORARY TABLE IF EXISTS tmp_precondition_assert;
CREATE TEMPORARY TABLE tmp_precondition_assert
(
    validation_result TINYINT NOT NULL,
    CONSTRAINT chk_common_code_final_precondition CHECK(validation_result=1)
);
INSERT INTO tmp_precondition_assert
VALUES
(
    IF(
        (SELECT COUNT(*) FROM cm_common_code_group)=63
        AND (SELECT COUNT(*) FROM cm_common_code)=421
        AND @group_change_count=19
        AND @code_change_count=72,
        1,
        0
    )
);
DROP TEMPORARY TABLE tmp_precondition_assert;

INSERT INTO cm_change_history
(
    change_history_id,
    target_database_name,
    target_table_name,
    target_record_id,
    action_type,
    change_story,
    created_by,
    created_dt,
    client_ip,
    program_id,
    status_code
)
SELECT
    CONCAT(
        'CM_CO_FINAL_G_',
        DATE_FORMAT(@batch_dt,'%Y%m%d%H%i%s'),
        '_',
        LPAD(ROW_NUMBER() OVER(ORDER BY group_code),3,'0')
    ),
    'te_common',
    'cm_common_code_group',
    group_code,
    'BATCH',
    CONCAT(
        group_code,
        ' Group complete census result: ',
        before_status_code,
        ' -> ',
        after_status_code,
        '. 설명, program_id, sort_no, JSON, 상태 및 하위 Code 전수 검증 완료.'
    ),
    @actor,
    @batch_dt,
    @client_ip,
    @program_id,
    'ACTIVE'
FROM tmp_group_lifecycle_change;

INSERT INTO cm_change_history
(
    change_history_id,
    target_database_name,
    target_table_name,
    target_record_id,
    action_type,
    change_story,
    created_by,
    created_dt,
    client_ip,
    program_id,
    status_code
)
SELECT
    CONCAT(
        'CM_CO_FINAL_C_',
        DATE_FORMAT(@batch_dt,'%Y%m%d%H%i%s'),
        '_',
        LPAD(ROW_NUMBER() OVER(ORDER BY group_code,code),3,'0')
    ),
    'te_common',
    'cm_common_code',
    CONCAT(group_code,':',code),
    'BATCH',
    CONCAT(
        group_code,
        '.',
        code,
        ' Code complete census result: ',
        before_status_code,
        ' -> ',
        after_status_code,
        '. 전체 품질 및 Repository 생명주기 재판정 완료.'
    ),
    @actor,
    @batch_dt,
    @client_ip,
    @program_id,
    'ACTIVE'
FROM tmp_code_lifecycle_change;

UPDATE cm_common_code_group g
JOIN tmp_group_lifecycle_change x
  ON x.group_code=g.group_code
SET
    g.lifecycle_status_code=x.after_status_code,
    g.updated_by=@actor,
    g.updated_dt=@batch_dt,
    g.client_ip=@client_ip,
    g.program_id=@program_id;

UPDATE cm_common_code c
JOIN tmp_code_lifecycle_change x
  ON x.group_code=c.group_code
 AND x.code=c.code
SET
    c.lifecycle_status_code=x.after_status_code,
    c.updated_by=@actor,
    c.updated_dt=@batch_dt,
    c.client_ip=@client_ip,
    c.program_id=@program_id;

SET @bad_group=(
    SELECT COUNT(*)
    FROM cm_common_code_group
    WHERE NULLIF(TRIM(group_name),'') IS NULL
       OR NULLIF(TRIM(group_description),'') IS NULL
       OR NULLIF(TRIM(program_id),'') IS NULL
       OR lifecycle_status_code NOT IN
          ('CREATE_MAINTAIN','DISPOSAL_CANDIDATE','DISPOSAL_IN_PROGRESS','DISPOSED','PRESERVE')
);
SET @bad_code=(
    SELECT COUNT(*)
    FROM cm_common_code
    WHERE NULLIF(TRIM(code_name),'') IS NULL
       OR NULLIF(TRIM(common_code_description),'') IS NULL
       OR NULLIF(TRIM(program_id),'') IS NULL
       OR lifecycle_status_code NOT IN
          ('CREATE_MAINTAIN','DISPOSAL_CANDIDATE','DISPOSAL_IN_PROGRESS','DISPOSED','PRESERVE')
       OR (common_code_json IS NOT NULL AND JSON_VALID(common_code_json)=0)
);
SET @duplicate_sort=(
    SELECT COUNT(*)
    FROM (
        SELECT group_code,sort_no
        FROM cm_common_code
        GROUP BY group_code,sort_no
        HAVING COUNT(*)>1
    ) duplicate_rows
);
SET @orphan_code=(
    SELECT COUNT(*)
    FROM cm_common_code c
    LEFT JOIN cm_common_code_group g ON g.group_code=c.group_code
    WHERE g.group_code IS NULL
);

DROP TEMPORARY TABLE IF EXISTS tmp_final_assert;
CREATE TEMPORARY TABLE tmp_final_assert
(
    validation_result TINYINT NOT NULL,
    CONSTRAINT chk_common_code_final_result CHECK(validation_result=1)
);
INSERT INTO tmp_final_assert
VALUES
(
    IF(
        @bad_group=0
        AND @bad_code=0
        AND @duplicate_sort=0
        AND @orphan_code=0
        AND (SELECT COUNT(*) FROM cm_common_code_group)=63
        AND (SELECT COUNT(*) FROM cm_common_code)=421
        AND (SELECT COUNT(*) FROM cm_common_code_group WHERE lifecycle_status_code='MODIFY')=0
        AND (SELECT COUNT(*) FROM cm_common_code WHERE lifecycle_status_code='MODIFY')=0,
        1,
        0
    )
);
DROP TEMPORARY TABLE tmp_final_assert;

COMMIT;

SELECT @group_change_count AS group_history_count,
       @code_change_count AS code_history_count,
       @group_change_count+@code_change_count AS total_history_count;
SELECT lifecycle_status_code,COUNT(*) AS group_count
FROM cm_common_code_group
GROUP BY lifecycle_status_code
ORDER BY lifecycle_status_code;
SELECT lifecycle_status_code,COUNT(*) AS code_count
FROM cm_common_code
GROUP BY lifecycle_status_code
ORDER BY lifecycle_status_code;
SELECT @bad_group AS bad_group,
       @bad_code AS bad_code,
       @duplicate_sort AS duplicate_sort,
       @orphan_code AS orphan_code;
SELECT group_code,group_name,status_code,lifecycle_status_code,program_id
FROM cm_common_code_group
ORDER BY sort_no,group_code;
SELECT group_code,code,code_name,status_code,lifecycle_status_code,program_id
FROM cm_common_code
ORDER BY group_code,sort_no,code;
