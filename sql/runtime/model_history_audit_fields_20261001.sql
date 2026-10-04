-- File Name : model_history_audit_fields_20261001.sql
-- Purpose   : Add the eight standard audit fields to te_common.model_history.
-- Scope     : DDL only; each field is added in its own idempotent ALTER statement.
-- Source    : COMMON.cm_common_code audit column types and comments.
-- Safety    : DROP is not used. Confirm each postcheck before marking complete.

USE te_common;

-- Precheck: expected to return zero rows before migration.
SELECT column_name
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'model_history'
  AND column_name IN (
    'created_by', 'created_dt', 'updated_by', 'updated_dt',
    'deleted_by', 'deleted_dt', 'program_id', 'client_ip'
  )
ORDER BY column_name;

ALTER TABLE model_history
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(99) NOT NULL DEFAULT 'SYSTEM'
  COMMENT '모델 이력을 최초 생성한 사용자 또는 실행 주체 식별자.';

ALTER TABLE model_history
  ADD COLUMN IF NOT EXISTS created_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  COMMENT '모델 이력 Object 최초 생성 일시.';

ALTER TABLE model_history
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(99) NOT NULL DEFAULT 'SYSTEM'
  COMMENT '모델 이력을 최종 수정한 사용자 또는 실행 주체 식별자.';

ALTER TABLE model_history
  ADD COLUMN IF NOT EXISTS updated_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  ON UPDATE CURRENT_TIMESTAMP
  COMMENT '모델 이력 Object 최종 수정 일시.';

ALTER TABLE model_history
  ADD COLUMN IF NOT EXISTS deleted_by VARCHAR(99) DEFAULT NULL
  COMMENT '모델 이력을 논리 삭제한 사용자 또는 실행 주체 식별자.';

ALTER TABLE model_history
  ADD COLUMN IF NOT EXISTS deleted_dt DATETIME DEFAULT NULL
  COMMENT '모델 이력 논리 삭제 처리 일시.';

ALTER TABLE model_history
  ADD COLUMN IF NOT EXISTS program_id VARCHAR(99) DEFAULT NULL
  COMMENT '모델 이력 생성·수정·삭제를 수행한 Program 식별자.';

ALTER TABLE model_history
  ADD COLUMN IF NOT EXISTS client_ip VARCHAR(99) DEFAULT NULL
  COMMENT '모델 이력 변경 요청이 발생한 Client IP 주소.';

-- Postcheck: expect all eight fields with their final definitions.
SELECT column_name, column_type, is_nullable, column_default, extra, column_comment
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'model_history'
  AND column_name IN (
    'created_by', 'created_dt', 'updated_by', 'updated_dt',
    'deleted_by', 'deleted_dt', 'program_id', 'client_ip'
  )
ORDER BY FIELD(
  column_name,
  'created_by', 'created_dt', 'updated_by', 'updated_dt',
  'deleted_by', 'deleted_dt', 'program_id', 'client_ip'
);
