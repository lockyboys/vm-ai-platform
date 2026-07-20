/*
File Name : repository_column_comment_patch_20260720.sql
Purpose   : Enrich Repository table/column comments after standard rename
Tables    : 13
Columns   : 18
*/

SET NAMES utf8mb4;

ALTER TABLE `te_story_platform`.`sp_domain`
    MODIFY COLUMN `sort_no` INT NOT NULL DEFAULT 0
        COMMENT 'Domain 표시 및 처리 순서를 제어하는 정렬 순번. Generator와 화면은 오름차순으로 해석한다.',
    COMMENT = 'Business 하위 Domain Object의 코드, 명칭, 설명과 정렬 순서를 관리하는 공식 Repository. Generator, Engine 및 AI는 Domain 분류와 탐색 기준으로 사용한다.';

ALTER TABLE `te_story_platform`.`sp_execution_history`
    MODIFY COLUMN `repository_status_code` VARCHAR(99) NULL DEFAULT NULL
        COMMENT 'Repository 저장 단계의 실행 결과 상태 코드. Runtime이 Repository 처리 성공·실패 상태를 기록한다.',
    MODIFY COLUMN `mongodb_status_code` VARCHAR(99) NULL DEFAULT NULL
        COMMENT 'MongoDB 저장 단계의 실행 결과 상태 코드. Runtime이 Collection 또는 Document 처리 상태를 기록한다.',
    MODIFY COLUMN `execution_status_code` VARCHAR(99) NOT NULL
        COMMENT '전체 Runtime 실행 결과 상태 코드. 실행 성공·실패·처리 중 상태 판정에 사용한다.',
    MODIFY COLUMN `history_status_code` VARCHAR(99) NOT NULL
        COMMENT 'Execution History 저장 처리 상태 코드. History Generator의 저장 진행 상태를 기록한다.',
    COMMENT = 'Story Programming Runtime의 Repository, MongoDB, 전체 실행 및 History 저장 결과를 추적하는 공식 실행 이력 Repository.';

ALTER TABLE `te_story_platform`.`sp_identifier_sequence`
    MODIFY COLUMN `sequence_dt` DATETIME NOT NULL
        COMMENT 'Identifier Sequence 적용 기준 일시. Identifier Engine이 Target, Prefix 및 기준 일시별 Sequence를 구분하는 Key로 사용한다.',
    COMMENT = 'Identifier Engine의 Target·Prefix·기준 일시별 현재 Sequence를 관리하는 공식 Repository. Engine은 이 값을 원천으로 식별자를 발급하며 임의 Hardcoding을 금지한다.';

ALTER TABLE `te_story_platform`.`sp_knowledge_type_hold`
    MODIFY COLUMN `sort_no` INT NOT NULL DEFAULT 0
        COMMENT 'Knowledge Type 표시 및 처리 순서를 제어하는 정렬 순번. 상위 Type 내 오름차순으로 해석한다.',
    COMMENT = 'Story를 구조화된 Knowledge로 분류하기 위한 Knowledge Type 계층의 HOLDING Repository. 승인 전 구조 검토와 분류 기준 보존에 사용한다.';

ALTER TABLE `te_common`.`cm_data_lifecycle_index`
    MODIFY COLUMN `disposed_dt` DATETIME NULL DEFAULT NULL
        COMMENT '데이터 자산의 실제 폐기 처리 일시. Lifecycle Engine이 보관 종료 및 폐기 완료 여부를 판단하는 기준이다.',
    COMMENT = 'Repository와 Storage에 분산된 데이터 자산의 보관·폐기 상태와 위치를 추적하는 공통 Lifecycle Index Repository.';

ALTER TABLE `te_common`.`cm_member_private`
    MODIFY COLUMN `birth_dt` DATETIME NULL DEFAULT NULL
        COMMENT '회원 출생 일시 정보. 개인정보 보호 정책과 사용자 연령 기반 처리에서 제한적으로 사용한다.',
    COMMENT = '회원의 민감 개인정보를 일반 회원 정보와 분리하여 관리하는 보호 Repository. 접근 권한과 개인정보 Lifecycle 정책을 적용한다.';

ALTER TABLE `te_common`.`cm_sequence`
    MODIFY COLUMN `sequence_dt` DATETIME NOT NULL
        COMMENT '공통 Sequence 적용 기준 일시. Sequence Code와 함께 초기화 범위별 현재 값을 구분하는 복합 Key이다.',
    COMMENT = 'Framework 공통 Sequence의 코드·기준 일시별 현재 값을 관리하는 공식 Repository. Generator와 Engine은 원자적 채번의 원천으로 사용한다.';

ALTER TABLE `te_common`.`cm_sequence_policy`
    MODIFY COLUMN `sort_no` INT NOT NULL DEFAULT 0
        COMMENT 'Sequence 초기화 정책의 표시 및 평가 순서를 제어하는 정렬 순번.',
    COMMENT = 'Sequence 초기화 주기와 날짜 형식을 정의하는 공통 정책 Repository. Sequence Engine은 정책 코드와 형식을 Metadata로 해석한다.';

ALTER TABLE `te_common`.`cm_sequence_policy_definition`
    MODIFY COLUMN `sequence_date_rule_code` VARCHAR(99) NOT NULL
        COMMENT 'Sequence 기준 일시 생성 규칙 코드. NO_RESET, YEARLY, MONTHLY, DAILY 범위의 날짜 Key 생성 규칙을 표현한다.',
    COMMENT = 'Sequence 기준 일시 유형과 생성 규칙 코드를 정의하는 공식 정책 Definition Repository. Engine은 규칙 코드를 해석하여 Sequence 범위를 결정한다.';

ALTER TABLE `te_common`.`cm_verified_sql_query`
    MODIFY COLUMN `created_ip` VARCHAR(99) NULL DEFAULT NULL
        COMMENT 'Verified SQL Query 최초 등록 요청의 클라이언트 IP 주소.',
    MODIFY COLUMN `updated_ip` VARCHAR(99) NULL DEFAULT NULL
        COMMENT 'Verified SQL Query 최종 수정 요청의 클라이언트 IP 주소.',
    MODIFY COLUMN `deleted_ip` VARCHAR(99) NULL DEFAULT NULL
        COMMENT 'Verified SQL Query 논리 삭제 요청의 클라이언트 IP 주소.',
    COMMENT = '검증이 완료된 SQL Query Object와 검증 결과, 실행 권한 판단 정보를 관리하는 공통 Repository. SQL Guard와 Generator의 공식 SQL 원천이다.';

ALTER TABLE `te_common`.`sql_guard_execution_log`
    MODIFY COLUMN `executed_dt` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'SQL Guard가 Verified SQL을 실제 실행한 일시. 실행 추적과 감사 기준 시각으로 사용한다.',
    COMMENT = 'SQL Guard의 사용자·메뉴·버튼·Query별 실행 결과와 오류를 추적하는 감사 Log Repository.';

ALTER TABLE `te_common`.`system_menu`
    MODIFY COLUMN `menu_sort_no` INT NOT NULL DEFAULT 0
        COMMENT 'Menu 표시 순서를 제어하는 정렬 순번. Menu Generator와 화면은 오름차순으로 해석한다.',
    COMMENT = 'System Menu의 코드, 명칭, URL과 표시 순서를 관리하는 공식 Menu Repository. 권한 및 화면 Generator가 사용한다.';

ALTER TABLE `te_common`.`system_menu_button`
    MODIFY COLUMN `button_sort_no` INT NOT NULL DEFAULT 0
        COMMENT 'Menu 내 Button 표시 순서를 제어하는 정렬 순번. Button Generator와 화면은 오름차순으로 해석한다.',
    COMMENT = 'System Menu 하위 Button의 CRUD 유형, Verified Query 연결과 표시 순서를 관리하는 공식 Button Repository.';

/* Verification */
SELECT
    table_schema,
    table_name,
    table_comment
FROM information_schema.tables
WHERE (table_schema, table_name) IN (
    ('te_story_platform', 'sp_domain'),
    ('te_story_platform', 'sp_execution_history'),
    ('te_story_platform', 'sp_identifier_sequence'),
    ('te_story_platform', 'sp_knowledge_type_hold'),
    ('te_common', 'cm_data_lifecycle_index'),
    ('te_common', 'cm_member_private'),
    ('te_common', 'cm_sequence'),
    ('te_common', 'cm_sequence_policy'),
    ('te_common', 'cm_sequence_policy_definition'),
    ('te_common', 'cm_verified_sql_query'),
    ('te_common', 'sql_guard_execution_log'),
    ('te_common', 'system_menu'),
    ('te_common', 'system_menu_button')
)
ORDER BY table_schema, table_name;

SELECT
    table_schema,
    table_name,
    column_name,
    column_type,
    column_comment
FROM information_schema.columns
WHERE (table_schema, table_name, column_name) IN (
    ('te_story_platform', 'sp_domain', 'sort_no'),
    ('te_story_platform', 'sp_execution_history', 'repository_status_code'),
    ('te_story_platform', 'sp_execution_history', 'mongodb_status_code'),
    ('te_story_platform', 'sp_execution_history', 'execution_status_code'),
    ('te_story_platform', 'sp_execution_history', 'history_status_code'),
    ('te_story_platform', 'sp_identifier_sequence', 'sequence_dt'),
    ('te_story_platform', 'sp_knowledge_type_hold', 'sort_no'),
    ('te_common', 'cm_data_lifecycle_index', 'disposed_dt'),
    ('te_common', 'cm_member_private', 'birth_dt'),
    ('te_common', 'cm_sequence', 'sequence_dt'),
    ('te_common', 'cm_sequence_policy', 'sort_no'),
    ('te_common', 'cm_sequence_policy_definition', 'sequence_date_rule_code'),
    ('te_common', 'cm_verified_sql_query', 'created_ip'),
    ('te_common', 'cm_verified_sql_query', 'updated_ip'),
    ('te_common', 'cm_verified_sql_query', 'deleted_ip'),
    ('te_common', 'sql_guard_execution_log', 'executed_dt'),
    ('te_common', 'system_menu', 'menu_sort_no'),
    ('te_common', 'system_menu_button', 'button_sort_no')
)
ORDER BY table_schema, table_name, ordinal_position;
