-- SPS Health Companion Knowledge Decision Update
-- Date: 2026-08-04 KST
-- Scope: sp_knowledge_hold metadata only
-- te_health_companion physical tables and rows are not modified.

UPDATE te_story_platform.sp_knowledge_hold
SET source_story_text = REPLACE(
        source_story_text,
        'DECISION: REDESIGN',
        'DECISION: MODIFY'
    ),
    updated_by = 'SYSTEM',
    updated_dt = CURRENT_TIMESTAMP,
    client_ip = '127.0.0.1',
    program_id = 'HEALTH_COMPANION_KNOWLEDGE_MODIFY_20260804'
WHERE knowledge_identifier IN (
    'KWH_TABLE_TE_HEALTH_COMPANION_AC_ACTION',
    'KWH_TABLE_TE_HEALTH_COMPANION_AT_AUDIT',
    'KWH_TABLE_TE_HEALTH_COMPANION_DC_DECISION',
    'KWH_TABLE_TE_HEALTH_COMPANION_DC_DECISION_DETAIL',
    'KWH_TABLE_TE_HEALTH_COMPANION_FB_FEEDBACK'
)
  AND active_yn = 'Y'
  AND deleted_yn = 'N'
  AND LOCATE('DECISION: REDESIGN', source_story_text) > 0;

-- Post-check: exactly five active rows must report DECISION: MODIFY.
SELECT knowledge_id, knowledge_identifier, knowledge_name, source_story_text,
       active_yn, deleted_yn, updated_dt, program_id
FROM te_story_platform.sp_knowledge_hold
WHERE knowledge_identifier IN (
    'KWH_TABLE_TE_HEALTH_COMPANION_AC_ACTION',
    'KWH_TABLE_TE_HEALTH_COMPANION_AT_AUDIT',
    'KWH_TABLE_TE_HEALTH_COMPANION_DC_DECISION',
    'KWH_TABLE_TE_HEALTH_COMPANION_DC_DECISION_DETAIL',
    'KWH_TABLE_TE_HEALTH_COMPANION_FB_FEEDBACK'
)
ORDER BY knowledge_identifier;
