-- SPS Identifier Blueprint Level 5 correction
-- Evidence: 2026-07-23 live Repository row SP_RP_BLUEPRINT_20260708_022644_00005
-- Before: LEVEL4_HIGH / level 4 / HHMMSSRRR / random_length 3
-- After : LEVEL5_NORMAL / level 5 / HHMMSSCC / random_length 0
-- Rule   : CC is a real centisecond. Random, millisecond and RRR are not used.

START TRANSACTION;

UPDATE te_story_platform.sp_identifier_blueprint
SET
    blueprint_code = 'LEVEL5_NORMAL',
    blueprint_name = 'Level 5 - Centisecond Identifier',
    object_level = 5,
    identifier_pattern = '{BUSINESS}_{DOMAIN}_{OBJECT}_{YYYYMMDD}_{HHMMSSCC}_{SEQ5}',
    date_format = 'YYYYMMDD',
    time_format = 'HHMMSSCC',
    random_length = 0,
    sequence_length = 5,
    sequence_scope_code = 'DAILY',
    sort_no = 50,
    enabled_yn = 'Y',
    status_code = 'ACTIVE',
    remark = 'Level 5 runtime identifier: HHMMSSCC uses real centiseconds; uniqueness is guaranteed by daily SEQ5.',
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = 'IDENTIFIER_BLUEPRINT_L5_FIX',
    program_id = 'runtime_20260723_000000_identifier_level5_fix.sql',
    client_ip = '127.0.0.1'
WHERE blueprint_id = 'SP_RP_BLUEPRINT_20260708_022644_00005'
  AND blueprint_code = 'LEVEL4_HIGH';

UPDATE te_common.cm_common_code
SET
    code = 'SPS_DATETIME_CENTISECOND_5',
    code_name = 'SPS 센티초 5자리 포맷',
    common_code_description = 'Business, Domain, Object Token, 센티초 시각과 5자리 Sequence로 Level 5 실행 식별자를 생성하는 SPS 포맷.',
    common_code_json = JSON_OBJECT(
        'format_pattern', '{BUSINESS}_{DOMAIN}_{OBJECT}_{YYYYMMDD}_{HHMMSSCC}_{SEQ:5}',
        'sequence_length', 5,
        'reset_policy_code', 'DAILY',
        'time_precision', 'CENTISECOND',
        'registration_basis', 'SPS_IDENTIFIER_LEVEL5_CONFIRMED'
    ),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = 'IDENTIFIER_BLUEPRINT_L5_FIX',
    program_id = 'runtime_20260723_000000_identifier_level5_fix.sql',
    client_ip = '127.0.0.1'
WHERE group_code = 'SPS_SEQUENCE_FORMAT'
  AND code = 'SPS_DATETIME_MILLISECOND_5';

SELECT
    blueprint_id,
    blueprint_code,
    object_level,
    identifier_pattern,
    date_format,
    time_format,
    random_length,
    sequence_length,
    sequence_scope_code,
    remark
FROM te_story_platform.sp_identifier_blueprint
WHERE blueprint_id = 'SP_RP_BLUEPRINT_20260708_022644_00005';

SELECT
    group_code,
    code,
    code_name,
    common_code_description,
    common_code_json
FROM te_common.cm_common_code
WHERE group_code = 'SPS_SEQUENCE_FORMAT'
  AND code = 'SPS_DATETIME_CENTISECOND_5';

COMMIT;
