"""Verified SQL 등록 시 Identifier Object를 Rule 계약으로 고르는지 검증한다(2026-10-25).

재현 버그: repository_table_object_reconcile 후 sp_object에 target_identifier_field='query_id'인
          활성 Object가 7개가 되자 _resolve_verified_sql_object_code가
          'must resolve exactly one Object ... object_count=7'로 모든 신규 등록을 거부했다.
수정 기준: RL_REGISTER_REPOSITORY_OBJECT 계약의 table_identifier_metadata에서 query_id를 쓰는
          테이블(cm_verified_sql_query)만 대상으로 Object를 고른다. 계약이 없거나 여전히 1개가
          아니면 추측하지 않고 오류를 낸다(잘못된 ID 발급 방지).
주의: 실제 DB 없이 가짜 fetch_all로만 검증한다.
"""
from __future__ import annotations

import pytest

from harness.mcp.tools import verified_sql_tools as tools

# 재조정 후 상황: query_id를 Identifier 필드로 가진 활성 Object 7개(원래 것 1 + 새로 생긴 6)
SP_OBJECT_ROWS = [
    {"object_code": "TE_COMMON_CM_VERIFIED_SQL_QUERY", "object_name": "te_common.cm_verified_sql_query",
     "target_identifier_field": "query_id"},
] + [
    {"object_code": f"TE_COMMON_EXTRA_{index}", "object_name": f"te_common.cm_verified_sql_query_bkp_{index}",
     "target_identifier_field": "query_id"}
    for index in range(6)
]


class FakeIdentifierDatabase:
    """sp_object 조회를 흉내 낸다. SQL에 object_name 필터가 있으면 그 이름만 돌려준다."""

    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def fetch_all(self, sql, params):
        self.queries.append((sql, params))
        field, *names = params
        matched = [row for row in self.rows if row["target_identifier_field"] == field]
        if "object_name" in sql:
            matched = [row for row in matched if row["object_name"] in names]
        return [{"object_code": row["object_code"]} for row in matched]


def test_resolves_single_object_from_rule_contract_tables():
    database = FakeIdentifierDatabase(SP_OBJECT_ROWS)
    code = tools._resolve_verified_sql_object_code(
        database, object_names=["te_common.cm_verified_sql_query"])
    assert code == "TE_COMMON_CM_VERIFIED_SQL_QUERY"
    assert "object_name" in database.queries[0][0]  # Rule 대상 테이블로 좁혀 조회해야 한다


def test_object_names_from_contract_metadata():
    contract = {"table_identifier_metadata": {
        "cm_verified_sql_query": {"target_identifier_field": "query_id", "identifier_target_code": "SQ"},
        "harness_source_audit": {"target_identifier_field": "id", "identifier_target_code": "OB"},
    }}
    assert tools._verified_sql_identifier_object_names(contract, "te_common") == ["te_common.cm_verified_sql_query"]


@pytest.mark.parametrize("contract", [{}, {"table_identifier_metadata": {}},
                                      {"table_identifier_metadata": "x"},
                                      {"table_identifier_metadata": {"t": {"target_identifier_field": "id"}}}])
def test_missing_contract_mapping_is_error(contract):
    # Rule에 query_id 매핑이 없으면 아무 Object나 고르지 않고 거부한다.
    with pytest.raises(ValueError):
        tools._verified_sql_identifier_object_names(contract, "te_common")


def test_still_ambiguous_is_error():
    rows = SP_OBJECT_ROWS + [dict(SP_OBJECT_ROWS[0], object_code="DUPLICATE")]
    with pytest.raises(ValueError):
        tools._resolve_verified_sql_object_code(
            FakeIdentifierDatabase(rows), object_names=["te_common.cm_verified_sql_query"])
