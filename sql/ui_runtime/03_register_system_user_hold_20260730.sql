/*
 * WITHDRAWN
 *
 * HOLD는 별도 sp_knowledge_hold 등록이 아니라 대상 상태 전환과
 * cm_change_history 기록으로 관리한다.
 *
 * 20260730 | Codex | 잘못된 HOLD 등록 방식이므로 실행 금지로 전환한다.
 */

SELECT 'WITHDRAWN_DO_NOT_EXECUTE' AS migration_status;
