/*
 * File Story
 *   기존 sp_object와 sp_object_lifecycle의 저장된 연결·이력을 읽어
 *   재등록이나 갱신 없이 Lifecycle 정합성 판단 근거를 반환한다.
 *
 * Change History
 *   20260803 | Codex | 기존 Object와 Lifecycle의 Link 및 Object 기준 이력을
 *   읽기 전용 Verified SQL 후보로 분리했음.
 *
 * Safety
 *   - INSERT, UPDATE, DELETE, DDL을 포함하지 않는다.
 *   - 저장된 sp_object를 재등록하거나 lifecycle_id를 갱신하지 않는다.
 *   - 결과 해석과 후속 보정은 이 Query가 cm_verified_sql_query에 등록·검증된 뒤에만 수행한다.
 */
SELECT
    object.object_id,
    object.object_code,
    object.object_name,
    object.status_code AS object_status_code,
    object.active_yn AS object_active_yn,
    object.lifecycle_id AS linked_lifecycle_id,
    lifecycle_by_link.object_lifecycle_id AS linked_lifecycle_row_id,
    lifecycle_by_link.object_id AS linked_lifecycle_object_id,
    lifecycle_by_link.lifecycle_status_code AS linked_lifecycle_status_code,
    lifecycle_by_link.lifecycle_event_code AS linked_lifecycle_event_code,
    lifecycle_by_link.effective_start_dt AS linked_effective_start_dt,
    lifecycle_by_link.effective_end_dt AS linked_effective_end_dt,
    lifecycle_by_object.object_lifecycle_id AS object_lifecycle_row_id,
    lifecycle_by_object.lifecycle_status_code AS object_lifecycle_status_code,
    lifecycle_by_object.lifecycle_event_code AS object_lifecycle_event_code,
    lifecycle_by_object.effective_start_dt AS object_effective_start_dt,
    lifecycle_by_object.effective_end_dt AS object_effective_end_dt
FROM te_story_platform.sp_object AS object
LEFT JOIN te_story_platform.sp_object_lifecycle AS lifecycle_by_link
    ON lifecycle_by_link.object_lifecycle_id = object.lifecycle_id
   AND lifecycle_by_link.deleted_dt IS NULL
LEFT JOIN te_story_platform.sp_object_lifecycle AS lifecycle_by_object
    ON lifecycle_by_object.object_id = object.object_id
   AND lifecycle_by_object.deleted_dt IS NULL
WHERE object.deleted_dt IS NULL
ORDER BY object.object_code, object.object_id, object_lifecycle_row_id;
