-- Restore Health Companion sp_knowledge_hold decisions to REDESIGN
-- Reverts only the five rows changed by Query ID CM_CO_TE_COMMON_CM_VERIFIED_SQL_QUERY_20260804_00009.
-- te_health_companion physical tables and rows are not modified.

UPDATE te_story_platform.sp_knowledge_hold
SET source_story_text = REPLACE(
        source_story_text,
        'DECISION: MODIFY',
        'DECISION: REDESIGN'
    ),
    updated_by = 'SYSTEM',
    updated_dt = CURRENT_TIMESTAMP,
    client_ip = '127.0.0.1',
    program_id = 'HEALTH_COMPANION_KNOWLEDGE_REDESIGN_RESTORE_20260804'
WHERE knowledge_identifier IN (
    'KWH_TABLE_TE_HEALTH_COMPANION_AC_ACTION',
    'KWH_TABLE_TE_HEALTH_COMPANION_AT_AUDIT',
    'KWH_TABLE_TE_HEALTH_COMPANION_DC_DECISION',
    'KWH_TABLE_TE_HEALTH_COMPANION_DC_DECISION_DETAIL',
    'KWH_TABLE_TE_HEALTH_COMPANION_FB_FEEDBACK'
)
  AND active_yn = 'Y'
  AND deleted_yn = 'N'
  AND program_id = 'HEALTH_COMPANION_KNOWLEDGE_MODIFY_20260804'
  AND LOCATE('DECISION: MODIFY', source_story_text) > 0;
