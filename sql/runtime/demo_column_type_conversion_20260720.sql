/*
File Name : demo_column_type_conversion_20260720.sql
Purpose   : SPS column type conversion demonstration
Safety    : TEMPORARY TABLE only. Production tables are not changed.
*/

SET NAMES utf8mb4;

DROP TEMPORARY TABLE IF EXISTS tmp_sps_column_type_demo;

CREATE TEMPORARY TABLE tmp_sps_column_type_demo
(
    demo_id BIGINT NOT NULL AUTO_INCREMENT,
    created_by VARCHAR(100),
    status_code VARCHAR(30),
    client_ip VARCHAR(50),
    display_name VARCHAR(100),
    version_no VARCHAR(30),
    business_date CHAR(8),
    summary_text TEXT,
    PRIMARY KEY (demo_id)
);

INSERT INTO tmp_sps_column_type_demo
(
    created_by,
    status_code,
    client_ip,
    display_name,
    version_no,
    business_date,
    summary_text
)
VALUES
(
    'SYSTEM',
    'ACTIVE',
    '127.0.0.1',
    'SPS Demo',
    '12',
    '20260720',
    'Column metadata conversion demonstration'
);

SELECT
    'BEFORE' AS demo_step,
    demo_id,
    created_by,
    status_code,
    client_ip,
    display_name,
    version_no,
    business_date,
    summary_text
FROM tmp_sps_column_type_demo;

/*
BIGINT AUTO_INCREMENT cannot remain AUTO_INCREMENT after conversion to VARCHAR.
Remove AUTO_INCREMENT first, then convert the identifier.
*/
ALTER TABLE tmp_sps_column_type_demo
    MODIFY COLUMN demo_id BIGINT NOT NULL;

ALTER TABLE tmp_sps_column_type_demo
    MODIFY COLUMN demo_id VARCHAR(99) NOT NULL,
    MODIFY COLUMN created_by VARCHAR(99),
    MODIFY COLUMN status_code VARCHAR(99),
    MODIFY COLUMN client_ip VARCHAR(99),
    MODIFY COLUMN display_name VARCHAR(150),
    MODIFY COLUMN version_no INT,
    MODIFY COLUMN summary_text VARCHAR(2000);

ALTER TABLE tmp_sps_column_type_demo
    ADD COLUMN business_dt DATETIME NULL AFTER business_date;

UPDATE tmp_sps_column_type_demo
SET
    demo_id = CONCAT('DEMO_ID_', LPAD(demo_id, 5, '0')),
    business_dt = STR_TO_DATE(business_date, '%Y%m%d');

ALTER TABLE tmp_sps_column_type_demo
    DROP COLUMN business_date;

SELECT
    'AFTER' AS demo_step,
    demo_id,
    created_by,
    status_code,
    client_ip,
    display_name,
    version_no,
    business_dt,
    summary_text
FROM tmp_sps_column_type_demo;

SHOW FULL COLUMNS FROM tmp_sps_column_type_demo;

DROP TEMPORARY TABLE IF EXISTS tmp_sps_column_type_demo;
