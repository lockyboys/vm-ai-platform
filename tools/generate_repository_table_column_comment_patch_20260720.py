# =============================================================================
# File Name : tools/generate_repository_table_column_comment_patch_20260720.py
# Purpose   : Generate full live Repository TABLE/COLUMN COMMENT patch and rollback
# =============================================================================

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase

DATABASE_ROLES = ("HEALTH_COMPANION", "STORY_PLATFORM", "COMMON")
OUTPUT_SQL = PROJECT_ROOT / "sql/runtime/repository_table_column_comment_patch_20260720.sql"
ROLLBACK_SQL = PROJECT_ROOT / "sql/runtime/repository_table_column_comment_rollback_20260720.sql"
AUDIT_CSV = PROJECT_ROOT / "outputs/reports/repository_table_column_comment_audit_20260720.csv"

TABLE_PURPOSES = {
    "cm_audit_policy": "감사 대상과 기록 범위를 정의하는 공통 감사 정책을 관리한다.",
    "cm_business_domain": "Business와 Domain의 공식 분류 코드 및 관계를 관리한다.",
    "cm_change_history": "Repository Object와 업무 데이터의 변경 이력을 추적한다.",
    "cm_code_inspection_result": "공통코드 구조와 값의 검사 결과 및 오류를 기록한다.",
    "cm_common_code": "Framework 전체에서 사용하는 공통코드 값과 구조화 지식을 관리한다.",
    "cm_common_code_group": "공통코드 Group의 의미, 범위 및 운영 정책을 관리한다.",
    "cm_consent_history": "사용자의 동의 유형별 획득·변경·철회 이력을 관리한다.",
    "cm_country": "국가 코드와 국가 명칭의 공식 Master를 관리한다.",
    "cm_data_classification": "데이터 보안·민감도 분류 기준의 공식 Master를 관리한다.",
    "cm_data_lifecycle_index": "Repository와 Storage에 분산된 데이터 자산의 보관·폐기 Lifecycle을 추적한다.",
    "cm_data_type": "Repository 자료 유형과 기본 분류·저장·보존 정책을 관리한다.",
    "cm_language": "지원 언어 코드와 언어 명칭의 공식 Master를 관리한다.",
    "cm_legal_retention_policy": "법적 근거에 따른 데이터 보존 기간과 폐기 조치를 관리한다.",
    "cm_locale": "언어·국가 조합별 Locale과 표시 형식을 관리한다.",
    "cm_login_history": "회원 로그인 시도 결과와 접속 정보를 추적한다.",
    "cm_member": "Framework 회원의 인증·식별·상태 정보를 관리한다.",
    "cm_member_private": "회원의 민감 개인정보를 일반 회원 정보와 분리하여 관리한다.",
    "cm_member_role": "회원과 Role 사이의 권한 부여 관계를 관리한다.",
    "cm_repository": "Book·Chapter·Section 계층의 Repository Data Object를 관리한다.",
    "cm_role": "Framework 권한 Role의 코드, 명칭 및 상태를 관리한다.",
    "cm_role_rule": "Role과 Rule의 N:N 관계를 해소하는 최소 매핑을 관리한다.",
    "cm_sequence": "공통 Sequence의 코드·기준 일시별 현재 값을 관리한다.",
    "cm_sequence_definition": "Sequence의 기능·Domain·정책·포맷·Prefix 구성을 정의한다.",
    "cm_sequence_format": "식별자와 Sequence 출력 포맷의 공식 Master를 관리한다.",
    "cm_sequence_format_definition": "Sequence Format Pattern과 설명을 정의한다.",
    "cm_sequence_policy": "Sequence 초기화 주기와 날짜 형식 정책을 관리한다.",
    "cm_sequence_policy_definition": "Sequence 기준 일시 유형과 생성 규칙을 정의한다.",
    "cm_sequence_rule": "분류·Domain·업무 유형별 Sequence 생성 규칙을 관리한다.",
    "cm_storage_policy": "데이터 유형별 저장소와 보존 정책 연결을 관리한다.",
    "cm_storage_repository": "물리·논리 Storage Repository의 연결 정보를 관리한다.",
    "cm_verified_sql_query": "검증 완료 SQL Query와 실행 통제 정보를 관리한다.",
    "ev_evidence": "Rule과 판단에서 사용하는 근거의 공식 정의를 관리한다.",
    "ev_evidence_reference": "근거가 참조하는 문서·논문·URL 출처를 관리한다.",
    "ev_evidence_version": "근거의 적용 기간과 Version 변경 이력을 관리한다.",
    "health_report": "회원 건강 Report의 생성 결과와 주요 건강 지표를 관리한다.",
    "md_object": "Metadata Object의 유형, 코드, 명칭 및 구조화 정의를 관리한다.",
    "md_relation": "Metadata Object 사이의 방향·Cardinality·관계 유형을 관리한다.",
    "rl_rule": "업무 Rule의 유형, 우선순위, Version 및 상태를 관리한다.",
    "rl_rule_action": "Rule 조건 충족 시 수행할 Action을 관리한다.",
    "rl_rule_condition": "Rule 평가 Field, Operator 및 조건 값을 관리한다.",
    "rl_rule_evidence": "Rule과 Evidence 사이의 근거 연결을 관리한다.",
    "sp_policy_rule_candidate": "정책 문서에서 추출된 Rule 후보와 신뢰도를 관리한다.",
    "sp_policy_rule_keyword": "정책·Rule 탐색에 사용하는 Keyword와 Category를 관리한다.",
    "sql_guard_execution_log": "SQL Guard의 사용자·화면·Query별 실행 결과를 추적한다.",
    "sql_guard_verification_log": "SQL Query 검증 단계별 판정과 오류를 추적한다.",
    "system_menu": "System Menu의 코드, 명칭, URL 및 표시 순서를 관리한다.",
    "system_menu_button": "Menu 하위 Button과 CRUD·Verified Query 연결을 관리한다.",
    "system_menu_button_crud_permission": "사용자 Role별 Menu·Button CRUD 권한을 관리한다.",
    "system_user": "System 사용자 계정과 Role 및 운영 상태를 관리한다.",
    "ac_action": "건강동행 판단 결과에 따라 수행되는 Action과 처리 상태를 관리한다.",
    "at_audit": "건강동행 Engine 판단과 실행 결과의 감사 기록을 관리한다.",
    "dc_decision": "건강동행 Rule과 Evidence 기반 Decision 결과를 관리한다.",
    "dc_decision_detail": "Decision에 사용된 입력 Field와 조건 평가 상세를 관리한다.",
    "fb_feedback": "사용자의 Decision·Action Feedback과 평가 결과를 관리한다.",
    "sp_attribute": "Story Programming Entity를 구성하는 Column Attribute 정의를 관리한다.",
    "sp_business": "Story Programming 최상위 Business Classification을 관리한다.",
    "sp_domain": "Business 하위 Domain의 코드, 명칭 및 분류를 관리한다.",
    "sp_entity": "Repository Table에 대응하는 Entity Object 정의를 관리한다.",
    "sp_erd": "Business·Domain별 ERD Object와 구조를 관리한다.",
    "sp_execution_history": "Runtime의 Repository·MongoDB·History 처리 결과를 추적한다.",
    "sp_identifier_blueprint": "Object Level별 Identifier Pattern과 생성 정책을 정의한다.",
    "sp_identifier_sequence": "Identifier Target·Prefix·기준 일시별 Sequence를 관리한다.",
    "sp_impact_analysis_result": "Repository 변경의 영향 Object와 Risk 분석 결과를 관리한다.",
    "sp_knowledge_hold": "승인 전 구조화 Knowledge Object를 보존하고 검토한다.",
    "sp_knowledge_relationship_hold": "승인 전 Knowledge 사이의 의미 관계를 보존하고 검토한다.",
    "sp_knowledge_type_hold": "승인 전 Knowledge Type 계층과 분류 기준을 보존하고 검토한다.",
    "sp_metadata": "Generator·Engine·AI가 해석하는 Story Programming Metadata를 관리한다.",
    "sp_object": "Framework가 인식하는 모든 Object Class와 Identifier 기준을 관리한다.",
    "sp_object_execution_link": "Object 실행 시도와 Repository·MongoDB 실행 대상을 연결한다.",
    "sp_object_lifecycle": "Object의 Lifecycle 상태와 Event 발생 이력을 관리한다.",
    "sp_relationship": "ERD와 범용 Object 사이의 의미 Relationship을 관리한다.",
    "sp_relationship_attribute": "Relationship의 Source·Target Attribute 매핑을 관리한다.",
    "sp_work_asset": "Work 수행 중 Generator·Engine·AI가 생성한 Asset을 관리한다.",
    "sp_work_item": "Work Session을 구성하는 개별 실행 단위를 관리한다.",
    "sp_work_session": "Runtime·Generator·Engine·AI의 최상위 Work Session을 관리한다.",
}

COMMON_CODE_GROUP_BY_COLUMN = {
    "status_code": "STATUS_CODE",
    "audit_type_code": "CHANGE_HISTORY_ACTION_TYPE",
    "action_type_code": "CHANGE_HISTORY_ACTION_TYPE",
    "reference_type_code": "CHANGE_HISTORY_ACTION_TYPE",
    "rule_type_code": "CHANGE_HISTORY_ACTION_TYPE",
    "action_status_code": "STATUS_CODE",
    "certified_level_code": "CM_LOG_LEVEL",
    "evidence_level_code": "CM_LOG_LEVEL",
    "lifecycle_event_code": "OBJECT_LIFECYCLE_STATUS",
    "data_type_code": "CM_DATA_TYPE",
    "engine_code": "ENGINE_TYPE",
    "function_code": "SPS_FUNCTION",
    "identifier_target_code": "SPS_IDENTIFIER_TARGET",
    "lifecycle_status_code": "OBJECT_LIFECYCLE_STATUS",
    "login_status_code": "AU_LOGIN_STATUS",
    "member_type_code": "MB_MEMBER_TYPE",
    "metadata_value_type_code": "METADATA_VALUE_TYPE",
    "object_type_code": "OBJECT_TYPE",
    "relationship_scope_code": "SPS_RELATIONSHIP_SCOPE",
    "repository_status_code": "REPOSITORY_STATUS",
    "risk_level_code": "HP_RISK_LEVEL",
    "role_code": "RL_ROLE",
    "severity_code": "CM_SEVERITY",
    "source_object_type_code": "SPS_RELATIONSHIP_OBJECT_TYPE",
    "target_object_type_code": "SPS_RELATIONSHIP_OBJECT_TYPE",
    "target_type_code": "SPS_METADATA_TARGET",
    "user_role_code": "RL_ROLE",
}

COMMON_CODE_GROUP_BY_TABLE_COLUMN = {
    ("STORY_PLATFORM", "sp_business", "business_code"): "CM_BUSINESS",
    ("STORY_PLATFORM", "sp_identifier_blueprint", "blueprint_code"): "SPS_IDENTIFIER_BLUEPRINT",
}

MASTER_REFERENCE_BY_COLUMN = {
    "audit_policy_code": "COMMON.cm_audit_policy(audit_policy_code)",
    "business_domain_code": "COMMON.cm_business_domain(business_domain_code)",
    "classification_code": "COMMON.cm_data_classification(classification_code)",
    "default_classification_code": "COMMON.cm_data_classification(classification_code)",
    "country_code": "COMMON.cm_country(country_code)",
    "language_code": "COMMON.cm_language(language_code)",
    "locale_code": "COMMON.cm_locale(locale_code)",
    "format_code": "COMMON.cm_sequence_format(format_code)",
    "policy_code": "COMMON.cm_sequence_policy(policy_code)",
    "sequence_code": "COMMON.cm_sequence_definition(sequence_code)",
    "evidence_code": "COMMON.ev_evidence(evidence_code)",
    "rule_code": "COMMON.rl_rule(rule_code)",
    "menu_code": "COMMON.system_menu(menu_code)",
    "button_code": "COMMON.system_menu_button(button_code)",
    "knowledge_type_code": "STORY_PLATFORM.sp_knowledge_type_hold(knowledge_type_code)",
    "object_code": "STORY_PLATFORM.sp_object(object_code)",
    "relationship_code": "STORY_PLATFORM.sp_relationship(relationship_code)",
}

EXACT_COLUMN_COMMENTS = {
    "created_dt": "Object 최초 생성 일시.",
    "created_by": "Object를 최초 생성한 사용자 또는 실행 주체 식별자.",
    "updated_dt": "Object 최종 수정 일시.",
    "updated_by": "Object를 최종 수정한 사용자 또는 실행 주체 식별자.",
    "deleted_dt": "Object 논리 삭제 처리 일시.",
    "deleted_by": "Object를 논리 삭제한 사용자 또는 실행 주체 식별자.",
    "program_id": "Object 생성·수정·삭제를 수행한 Program 식별자.",
    "client_ip": "Object 변경 요청이 발생한 Client IP 주소.",
    "remark": "Object 처리와 판단에 필요한 추가 비고.",
    "sort_no": "표시 및 처리 순서를 제어하는 정렬 순번.",
    "version_num": "Object Version을 문자열로 표현한 번호.",
    "active_yn": "Object 활성 여부. Y 또는 N으로 관리한다.",
}


def q(identifier: str) -> str:
    return "`" + str(identifier).replace("`", "``") + "`"


def sql_string(value: str) -> str:
    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace("'", "''")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )
    return "'" + escaped + "'"


def truncate_utf8(value: str, max_bytes: int) -> str:
    data = value.encode("utf-8")
    if len(data) <= max_bytes:
        return value
    data = data[:max_bytes]
    while data:
        try:
            return data.decode("utf-8").rstrip()
        except UnicodeDecodeError:
            data = data[:-1]
    return ""


def human_label(column_name: str) -> str:
    return column_name.replace("_", " ").title()


def generated_column_comment(table_name: str, column_name: str) -> str:
    if column_name in EXACT_COLUMN_COMMENTS:
        return EXACT_COLUMN_COMMENTS[column_name]

    label = human_label(column_name)
    suffixes = (
        ("_id", f"{label} 식별자. {table_name} Object와 관련 Object를 식별하거나 연결한다."),
        ("_code", f"{label} 코드. Repository Metadata가 정의한 코드 체계로 관리한다."),
        ("_name", f"{label} 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다."),
        ("_description", f"{label} 설명. Object의 목적, 의미 및 적용 범위를 관리한다."),
        ("_json", f"{label} 구조화 JSON. Generator, Engine 및 AI가 해석하는 확장 Metadata를 관리한다."),
        ("_dt", f"{label} 일시. Object의 해당 Event 발생 시점을 관리한다."),
        ("_yn", f"{label} 여부. Y 또는 N 값으로 관리한다."),
        ("_no", f"{label} 순번. 정렬 또는 처리 순서를 정수로 관리한다."),
        ("_num", f"{label} 번호. 의미 있는 문자열 번호로 관리한다."),
        ("_by", f"{label} 처리 주체 식별자."),
        ("_ip", f"{label} Client IP 주소."),
        ("_url", f"{label} URL 주소."),
        ("_score", f"{label} 점수. 평가 또는 판단의 수치 결과를 관리한다."),
        ("_count", f"{label} 건수."),
        ("_value", f"{label} 값. 해당 Object 속성의 실제 값을 관리한다."),
        ("_text", f"{label} Text 값."),
    )
    for suffix, comment in suffixes:
        if column_name.endswith(suffix):
            return comment
    return f"{label} 값. {table_name} Object의 해당 속성을 관리한다."


def reference_for(role: str, table: str, column: str) -> tuple[str, str] | None:
    group = COMMON_CODE_GROUP_BY_TABLE_COLUMN.get((role, table, column))
    if group is None:
        group = COMMON_CODE_GROUP_BY_COLUMN.get(column)
    if group:
        return (
            "COMMON_CODE",
            f"te_common.cm_common_code(group_code={group})",
        )
    master = MASTER_REFERENCE_BY_COLUMN.get(column)
    if master:
        return ("MASTER_REPOSITORY", master)
    return None


def build_column_comment(
    role: str,
    table: str,
    column: str,
    existing_comment: str,
) -> tuple[str, str, str]:
    base = str(existing_comment or "").strip()
    if not base:
        base = generated_column_comment(table, column)

    reference = reference_for(role, table, column)
    reference_type = ""
    reference_target = ""
    if reference:
        reference_type, reference_target = reference
        if reference_type == "COMMON_CODE":
            group = reference_target.split("group_code=", 1)[1].rstrip(")")
            guide = (
                f"REFERENCE: te_common.cm_common_code의 group_code={group}. "
                "Generator, Engine 및 AI는 해당 Group의 code를 해석한다."
            )
        else:
            guide = (
                f"REFERENCE: {reference_target}. "
                "해당 Master Repository를 공식 연결 원천으로 사용한다."
            )
        if reference_target not in base and guide not in base:
            base = f"{base} {guide}"
    elif column.endswith("_code"):
        guide = (
            "REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 "
            "Metadata에서 확정해야 한다."
        )
        if "REFERENCE:" not in base:
            base = f"{base} {guide}"
        reference_type = "UNRESOLVED"

    return truncate_utf8(base, 900), reference_type, reference_target


def build_table_comment(role: str, table: str, existing_comment: str) -> str:
    existing = str(existing_comment or "").strip()
    if len(existing.encode("utf-8")) >= 900 and (
        "PURPOSE" in existing.upper() or "REPOSITORY" in existing.upper()
    ):
        return existing

    purpose = TABLE_PURPOSES.get(
        table,
        existing or f"{table} Object의 정의와 실행 정보를 관리한다.",
    )
    if table.endswith("_history") or table.endswith("_log") or "audit" in table:
        ssot = "해당 이력과 실행 결과의 공식 원천"
    else:
        ssot = "해당 Object 정의와 관계의 단일 원천"

    comment = (
        f"PURPOSE: {purpose} "
        f"ROLE: {role} 공식 Repository. "
        f"SSOT: {ssot}. "
        "ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 "
        "해석하며 값과 규칙의 Hardcoding을 금지한다."
    )
    return truncate_utf8(comment, 1800)


def resolve_database_names() -> dict[str, str]:
    names: dict[str, str] = {}
    for role in DATABASE_ROLES:
        database = CommonDatabase(database_role=role)
        try:
            names[role] = str(database.database_name)
        finally:
            database.close()
    return names


def load_inventory(
    database: CommonDatabase,
    database_names: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]]]:
    schemas = tuple(database_names.values())
    placeholders = ", ".join(["%s"] * len(schemas))

    tables = database.fetch_all(
        f"""
        SELECT
            table_schema,
            table_name,
            table_comment
        FROM information_schema.tables
        WHERE table_schema IN ({placeholders})
          AND table_type = 'BASE TABLE'
          AND table_name NOT REGEXP '_backup_'
        ORDER BY FIELD(table_schema, %s, %s, %s), table_name
        """,
        (
            *schemas,
            database_names["HEALTH_COMPANION"],
            database_names["STORY_PLATFORM"],
            database_names["COMMON"],
        ),
    )

    columns = database.fetch_all(
        f"""
        SELECT
            table_schema,
            table_name,
            column_name,
            ordinal_position,
            column_comment
        FROM information_schema.columns
        WHERE table_schema IN ({placeholders})
          AND table_name NOT REGEXP '_backup_'
        ORDER BY
            FIELD(table_schema, %s, %s, %s),
            table_name,
            ordinal_position
        """,
        (
            *schemas,
            database_names["HEALTH_COMPANION"],
            database_names["STORY_PLATFORM"],
            database_names["COMMON"],
        ),
    )

    by_table: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for column in columns:
        by_table[(str(column["table_schema"]), str(column["table_name"]))].append(column)
    return tables, dict(by_table)


# MariaDB may place a column-level CHECK clause after COMMENT, for example:
#   ... COMMENT '변경 전 JSON' CHECK (json_valid(`before_value_json`))
# Therefore COMMENT must be removed wherever it appears in the column
# definition instead of assuming that it is the final clause.
COLUMN_COMMENT_RE = re.compile(
    r"\s+COMMENT\s+'(?:\\.|''|[^'])*'",
    flags=re.IGNORECASE,
)


def show_create_column_definitions(
    database: CommonDatabase,
    schema: str,
    table: str,
    columns: list[dict[str, Any]],
) -> dict[str, str]:
    row = database.fetch_one(f"SHOW CREATE TABLE {q(schema)}.{q(table)}")
    create_sql = str(row.get("Create Table") or row.get("Create View") or "")
    if not create_sql:
        raise RuntimeError(f"SHOW CREATE TABLE result missing: {schema}.{table}")

    definitions: dict[str, str] = {}
    wanted = {str(column["column_name"]) for column in columns}
    for raw_line in create_sql.splitlines():
        line = raw_line.strip().rstrip(",")
        if not line.startswith("`"):
            continue
        match = re.match(r"^`((?:``|[^`])*)`\s+(.*)$", line)
        if not match:
            continue
        name = match.group(1).replace("``", "`")
        if name not in wanted:
            continue
        definition = match.group(2)
        definition_without_comment = COLUMN_COMMENT_RE.sub("", definition).rstrip()
        old_comment = next(
            str(column.get("column_comment") or "")
            for column in columns
            if str(column["column_name"]) == name
        )
        if old_comment and definition_without_comment == definition:
            raise RuntimeError(
                f"Could not remove existing COMMENT from {schema}.{table}.{name}"
            )
        definitions[name] = definition_without_comment

    missing = wanted - set(definitions)
    if missing:
        raise RuntimeError(
            f"SHOW CREATE parser missed columns in {schema}.{table}: {sorted(missing)}"
        )
    return definitions


def load_foreign_keys(
    database: CommonDatabase,
    schemas: tuple[str, ...],
) -> list[dict[str, Any]]:
    placeholders = ", ".join(["%s"] * len(schemas))
    rows = database.fetch_all(
        f"""
        SELECT
            k.constraint_schema,
            k.table_name,
            k.constraint_name,
            k.column_name,
            k.referenced_table_schema,
            k.referenced_table_name,
            k.referenced_column_name,
            k.ordinal_position,
            r.update_rule,
            r.delete_rule
        FROM information_schema.key_column_usage k
        JOIN information_schema.referential_constraints r
          ON r.constraint_schema = k.constraint_schema
         AND r.table_name = k.table_name
         AND r.constraint_name = k.constraint_name
        WHERE k.referenced_table_name IS NOT NULL
          AND k.constraint_schema IN ({placeholders})
        ORDER BY
            k.constraint_schema,
            k.table_name,
            k.constraint_name,
            k.ordinal_position
        """,
        schemas,
    )

    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row["constraint_schema"]),
            str(row["table_name"]),
            str(row["constraint_name"]),
        )
        fk = grouped.setdefault(
            key,
            {
                "schema": key[0],
                "table": key[1],
                "name": key[2],
                "referenced_schema": str(row["referenced_table_schema"]),
                "referenced_table": str(row["referenced_table_name"]),
                "columns": [],
                "referenced_columns": [],
                "update_rule": str(row["update_rule"]),
                "delete_rule": str(row["delete_rule"]),
            },
        )
        fk["columns"].append(str(row["column_name"]))
        fk["referenced_columns"].append(str(row["referenced_column_name"]))
    return list(grouped.values())


def fk_drop_sql(fk: dict[str, Any]) -> str:
    return (
        f"ALTER TABLE {q(fk['schema'])}.{q(fk['table'])} "
        f"DROP FOREIGN KEY {q(fk['name'])};"
    )


def fk_add_sql(fk: dict[str, Any]) -> str:
    columns = ", ".join(q(column) for column in fk["columns"])
    referenced = ", ".join(q(column) for column in fk["referenced_columns"])
    return (
        f"ALTER TABLE {q(fk['schema'])}.{q(fk['table'])} "
        f"ADD CONSTRAINT {q(fk['name'])} FOREIGN KEY ({columns}) "
        f"REFERENCES {q(fk['referenced_schema'])}.{q(fk['referenced_table'])} "
        f"({referenced}) ON UPDATE {fk['update_rule']} "
        f"ON DELETE {fk['delete_rule']};"
    )


def column_definition_with_comment(definition: str, comment: str) -> str:
    comment_clause = f" COMMENT {sql_string(comment)}"
    check_match = re.search(r"\s+CHECK\s*\(", definition, flags=re.IGNORECASE)
    if check_match:
        # Preserve MariaDB's SHOW CREATE column-clause order:
        # ... COMMENT '...' CHECK (...)
        return (
            definition[: check_match.start()]
            + comment_clause
            + definition[check_match.start() :]
        )
    return definition + comment_clause


def alter_table_sql(
    schema: str,
    table: str,
    table_comment: str | None,
    column_changes: list[tuple[str, str, str]],
) -> str:
    clauses: list[str] = []
    for column_name, definition, comment in column_changes:
        clauses.append(
            f"MODIFY COLUMN {q(column_name)} "
            f"{column_definition_with_comment(definition, comment)}"
        )
    if table_comment is not None:
        clauses.append(f"COMMENT = {sql_string(table_comment)}")
    return (
        f"ALTER TABLE {q(schema)}.{q(table)}\n    "
        + ",\n    ".join(clauses)
        + ";"
    )


def generate() -> dict[str, Any]:
    database_names = resolve_database_names()
    role_by_schema = {schema: role for role, schema in database_names.items()}
    database = CommonDatabase(database_role="COMMON")

    try:
        tables, columns_by_table = load_inventory(database, database_names)
        foreign_keys = load_foreign_keys(database, tuple(database_names.values()))

        patch_tables: list[dict[str, Any]] = []
        audit_rows: list[dict[str, Any]] = []
        changed_column_keys: set[tuple[str, str, str]] = set()

        for table_row in tables:
            schema = str(table_row["table_schema"])
            table = str(table_row["table_name"])
            role = role_by_schema[schema]
            columns = columns_by_table[(schema, table)]
            definitions = show_create_column_definitions(
                database, schema, table, columns
            )

            old_table_comment = str(table_row.get("table_comment") or "")
            new_table_comment = build_table_comment(role, table, old_table_comment)
            table_changed = new_table_comment != old_table_comment

            column_changes: list[dict[str, Any]] = []
            for column in columns:
                name = str(column["column_name"])
                old_comment = str(column.get("column_comment") or "")
                new_comment, reference_type, reference_target = build_column_comment(
                    role, table, name, old_comment
                )
                changed = new_comment != old_comment
                if changed:
                    changed_column_keys.add((schema, table, name))
                    column_changes.append(
                        {
                            "column_name": name,
                            "definition": definitions[name],
                            "old_comment": old_comment,
                            "new_comment": new_comment,
                        }
                    )
                audit_rows.append(
                    {
                        "database_role": role,
                        "table_schema": schema,
                        "table_name": table,
                        "column_name": name,
                        "old_comment": old_comment,
                        "new_comment": new_comment,
                        "reference_type": reference_type,
                        "reference_target": reference_target,
                        "status": "UPDATED" if changed else "UNCHANGED",
                    }
                )

            if table_changed or column_changes:
                patch_tables.append(
                    {
                        "database_role": role,
                        "schema": schema,
                        "table": table,
                        "old_table_comment": old_table_comment,
                        "new_table_comment": new_table_comment,
                        "table_changed": table_changed,
                        "columns": column_changes,
                    }
                )

        affected_foreign_keys = []
        for fk in foreign_keys:
            child_keys = {
                (fk["schema"], fk["table"], column)
                for column in fk["columns"]
            }
            parent_keys = {
                (fk["referenced_schema"], fk["referenced_table"], column)
                for column in fk["referenced_columns"]
            }
            if changed_column_keys & (child_keys | parent_keys):
                affected_foreign_keys.append(fk)

    finally:
        database.close()

    header = [
        "/*",
        "File Name : repository_table_column_comment_patch_20260720.sql",
        "Purpose   : Full live Repository TABLE/COLUMN COMMENT maintenance",
        f"Tables    : {len(tables)} live / {len(patch_tables)} changed",
        f"Columns   : {sum(len(v) for v in columns_by_table.values())} live / "
        f"{len(changed_column_keys)} changed",
        f"FK Rebuild: {len(affected_foreign_keys)} constraints",
        "Data Change: NONE",
        "*/",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
        "/* Drop affected Foreign Keys */",
    ]
    patch_lines = header + [fk_drop_sql(fk) for fk in affected_foreign_keys]

    for item in patch_tables:
        forward_columns = [
            (
                column["column_name"],
                column["definition"],
                column["new_comment"],
            )
            for column in item["columns"]
        ]
        patch_lines.extend(
            [
                "",
                f"/* {item['schema']}.{item['table']} */",
                alter_table_sql(
                    item["schema"],
                    item["table"],
                    item["new_table_comment"] if item["table_changed"] else None,
                    forward_columns,
                ),
            ]
        )

    patch_lines.extend(["", "/* Restore Foreign Keys */"])
    patch_lines.extend(fk_add_sql(fk) for fk in affected_foreign_keys)
    patch_lines.extend(
        [
            "",
            "SET FOREIGN_KEY_CHECKS = 1;",
            "",
            "/* Verification */",
            "SELECT table_schema, COUNT(*) AS table_count,",
            "       SUM(CASE WHEN table_comment = '' THEN 1 ELSE 0 END) AS empty_table_comment_count",
            "FROM information_schema.tables",
            "WHERE table_schema IN ("
            + ", ".join(sql_string(value) for value in database_names.values())
            + ")",
            "  AND table_type = 'BASE TABLE'",
            "  AND table_name NOT REGEXP '_backup_'",
            "GROUP BY table_schema",
            "ORDER BY table_schema;",
            "",
            "SELECT table_schema, COUNT(*) AS column_count,",
            "       SUM(CASE WHEN column_comment = '' THEN 1 ELSE 0 END) AS empty_column_comment_count",
            "FROM information_schema.columns",
            "WHERE table_schema IN ("
            + ", ".join(sql_string(value) for value in database_names.values())
            + ")",
            "  AND table_name NOT REGEXP '_backup_'",
            "GROUP BY table_schema",
            "ORDER BY table_schema;",
            "",
            "SELECT COUNT(*) AS unresolved_code_comment_count",
            "FROM information_schema.columns",
            "WHERE table_schema IN ("
            + ", ".join(sql_string(value) for value in database_names.values())
            + ")",
            "  AND table_name NOT REGEXP '_backup_'",
            "  AND column_name LIKE '%\\_code'",
            "  AND column_comment LIKE '%REFERENCE: UNRESOLVED%';",
        ]
    )

    rollback_header = [
        "/*",
        "File Name : repository_table_column_comment_rollback_20260720.sql",
        "Purpose   : Restore TABLE/COLUMN COMMENT values captured before patch",
        "Data Change: NONE",
        "*/",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
        "/* Drop affected Foreign Keys */",
    ]
    rollback_lines = rollback_header + [
        fk_drop_sql(fk) for fk in affected_foreign_keys
    ]

    for item in reversed(patch_tables):
        rollback_columns = [
            (
                column["column_name"],
                column["definition"],
                column["old_comment"],
            )
            for column in item["columns"]
        ]
        rollback_lines.extend(
            [
                "",
                f"/* {item['schema']}.{item['table']} */",
                alter_table_sql(
                    item["schema"],
                    item["table"],
                    item["old_table_comment"] if item["table_changed"] else None,
                    rollback_columns,
                ),
            ]
        )

    rollback_lines.extend(["", "/* Restore Foreign Keys */"])
    rollback_lines.extend(fk_add_sql(fk) for fk in affected_foreign_keys)
    rollback_lines.extend(["", "SET FOREIGN_KEY_CHECKS = 1;"])

    OUTPUT_SQL.parent.mkdir(parents=True, exist_ok=True)
    ROLLBACK_SQL.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SQL.write_text("\n".join(patch_lines) + "\n", encoding="utf-8")
    ROLLBACK_SQL.write_text("\n".join(rollback_lines) + "\n", encoding="utf-8")

    fields = [
        "database_role",
        "table_schema",
        "table_name",
        "column_name",
        "old_comment",
        "new_comment",
        "reference_type",
        "reference_target",
        "status",
    ]
    with AUDIT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit_rows)

    return {
        "live_table_count": len(tables),
        "changed_table_count": len(patch_tables),
        "live_column_count": sum(len(v) for v in columns_by_table.values()),
        "changed_column_count": len(changed_column_keys),
        "fk_rebuild_count": len(affected_foreign_keys),
        "output_sql": str(OUTPUT_SQL.relative_to(PROJECT_ROOT)),
        "rollback_sql": str(ROLLBACK_SQL.relative_to(PROJECT_ROOT)),
        "audit_csv": str(AUDIT_CSV.relative_to(PROJECT_ROOT)),
    }


def main() -> int:
    result = generate()
    for key, value in result.items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
