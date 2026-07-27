---
title: te_common ERD
---
erDiagram
    rl_rule {
        VARCHAR rule_id PK
        VARCHAR rule_code UK
        VARCHAR rule_name
        VARCHAR rule_type_code
        VARCHAR rule_group_code "nullable"
        VARCHAR rule_description "nullable"
        INT priority_no
        VARCHAR status_code
        VARCHAR version_num "nullable"
        VARCHAR remark "nullable"
        INT sort_no
        DATETIME created_dt
        VARCHAR created_by
        DATETIME updated_dt
        VARCHAR updated_by
        VARCHAR deleted_by "nullable"
        DATETIME deleted_dt "nullable"
        VARCHAR program_id "nullable"
        VARCHAR client_ip "nullable"
    }
    ev_evidence {
        VARCHAR evidence_id PK
        VARCHAR evidence_code UK
        VARCHAR evidence_name
        VARCHAR evidence_level_code
        VARCHAR evidence_category_code
        VARCHAR organization_name "nullable"
        VARCHAR source_title "nullable"
        DATETIME published_dt "nullable"
        DATETIME effective_from_dt "nullable"
        DATETIME effective_to_dt "nullable"
        VARCHAR version_num "nullable"
        VARCHAR status_code
        VARCHAR summary "nullable"
        VARCHAR remark "nullable"
        INT sort_no
        DATETIME created_dt
        VARCHAR created_by
        DATETIME updated_dt
        VARCHAR updated_by
        VARCHAR deleted_by "nullable"
        DATETIME deleted_dt "nullable"
        VARCHAR program_id "nullable"
        VARCHAR client_ip "nullable"
    }
    cm_role {
        VARCHAR role_id PK
        VARCHAR role_code UK
        VARCHAR role_name
        DATETIME created_dt
        VARCHAR created_by
        DATETIME updated_dt
        VARCHAR updated_by
        VARCHAR client_ip "nullable"
        VARCHAR deleted_by "nullable"
        DATETIME deleted_dt "nullable"
        VARCHAR program_id "nullable"
        VARCHAR status_code
    }
    cm_role_rule {
        VARCHAR role_id PK
        VARCHAR rule_id PK
        DATETIME created_dt
        VARCHAR created_by
        DATETIME updated_dt "nullable"
        VARCHAR updated_by "nullable"
        VARCHAR deleted_by "nullable"
        DATETIME deleted_dt "nullable"
        VARCHAR program_id
        VARCHAR client_ip "nullable"
    }
    rl_rule_evidence {
        VARCHAR rule_evidence_id PK
        VARCHAR rule_id
        VARCHAR evidence_id
        CHAR primary_yn
        VARCHAR remark "nullable"
        DATETIME created_dt
        VARCHAR created_by
        DATETIME updated_dt
        VARCHAR updated_by
        VARCHAR deleted_by "nullable"
        DATETIME deleted_dt "nullable"
        VARCHAR program_id "nullable"
        VARCHAR client_ip "nullable"
        VARCHAR status_code
    }
    cm_member_role {
        VARCHAR member_role_id PK
        VARCHAR member_id
        VARCHAR role_id
        DATETIME created_dt
        VARCHAR created_by
        DATETIME updated_dt
        VARCHAR updated_by
        VARCHAR client_ip "nullable"
        VARCHAR deleted_by "nullable"
        DATETIME deleted_dt "nullable"
        VARCHAR program_id "nullable"
        VARCHAR status_code
    }
    ev_evidence_reference {
        VARCHAR reference_id PK
        VARCHAR evidence_id
        VARCHAR reference_type_code
        VARCHAR reference_title
        VARCHAR organization_name "nullable"
        VARCHAR author_name "nullable"
        VARCHAR journal_name "nullable"
        VARCHAR doi "nullable"
        VARCHAR pmid "nullable"
        VARCHAR reference_url "nullable"
        DATETIME published_dt "nullable"
        VARCHAR remark "nullable"
        INT sort_no
        DATETIME created_dt
        VARCHAR created_by
        DATETIME updated_dt
        VARCHAR updated_by
        VARCHAR deleted_by "nullable"
        DATETIME deleted_dt "nullable"
        VARCHAR program_id "nullable"
        VARCHAR client_ip "nullable"
        VARCHAR status_code
    }
    ev_evidence_version {
        VARCHAR evidence_version_id PK
        VARCHAR evidence_id
        VARCHAR version_num "nullable"
        DATETIME effective_from_dt
        DATETIME effective_to_dt "nullable"
        VARCHAR change_summary "nullable"
        VARCHAR remark "nullable"
        DATETIME created_dt
        VARCHAR created_by
        DATETIME updated_dt
        VARCHAR updated_by
        VARCHAR deleted_by "nullable"
        DATETIME deleted_dt "nullable"
        VARCHAR program_id "nullable"
        VARCHAR client_ip "nullable"
        VARCHAR status_code
    }
    rl_rule_action {
        VARCHAR rule_action_id PK
        VARCHAR rule_id
        VARCHAR action_type_code
        VARCHAR action_value "nullable"
        INT sort_no
        VARCHAR remark "nullable"
        DATETIME created_dt
        VARCHAR created_by
        DATETIME updated_dt
        VARCHAR updated_by
        VARCHAR deleted_by "nullable"
        DATETIME deleted_dt "nullable"
        VARCHAR program_id "nullable"
        VARCHAR client_ip "nullable"
        VARCHAR status_code
    }
    rl_rule_condition {
        VARCHAR condition_id PK
        VARCHAR rule_id
        INT sort_no
        VARCHAR field_code
        VARCHAR operator_code
        VARCHAR condition_value
        VARCHAR logical_operator_code "nullable"
        VARCHAR remark "nullable"
        DATETIME created_dt
        VARCHAR created_by
        DATETIME updated_dt
        VARCHAR updated_by
        VARCHAR deleted_by "nullable"
        DATETIME deleted_dt "nullable"
        VARCHAR program_id "nullable"
        VARCHAR client_ip "nullable"
        VARCHAR status_code
    }
    cm_role ||--o{ cm_member_role : "role_id→role_id"
    cm_role ||--o{ cm_role_rule : "role_id→role_id"
    rl_rule ||--o{ cm_role_rule : "rule_id→rule_id"
    ev_evidence ||--o{ ev_evidence_reference : "evidence_id→evidence_id"
    ev_evidence ||--o{ ev_evidence_version : "evidence_id→evidence_id"
    rl_rule ||--o{ rl_rule_action : "rule_id→rule_id"
    rl_rule ||--o{ rl_rule_condition : "rule_id→rule_id"
    ev_evidence ||--o{ rl_rule_evidence : "evidence_id→evidence_id"
    rl_rule ||--o{ rl_rule_evidence : "rule_id→rule_id"
