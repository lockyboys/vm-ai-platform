/*
 * HOLD
 * 20260731 | Codex | UI Object Level 4 보정안 철회.
 *
 * Reason
 * - 확정 계약: Table Object는 Level 3이다.
 * - Level 4는 별도 Attribute 또는 Relationship Attribute Object에만 사용한다.
 * - UI의 미완료 범위는 Object Level 보정이 아니라 UI ERD 등록이다.
 *
 * 이 파일은 실행하지 않는다. DB 구조와 데이터를 변경하지 않는다.
 */
SELECT 'HOLD: UI Object Level 4 correction is withdrawn; implement UI ERD registration instead.'
    AS hold_reason;
