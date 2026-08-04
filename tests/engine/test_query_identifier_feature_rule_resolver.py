"""Tests for Rule-backed Verified SQL Query-ID feature validation."""

from __future__ import annotations

import json

import pytest

from engine.common.query_identifier_feature_rule_resolver import (
    QueryIdentifierFeatureRuleResolver,
)


class _RuleDatabase:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def fetch_all(
        self,
        sql: str,
        params: tuple[object, ...],
    ) -> list[dict[str, object]]:
        self.calls.append((sql, params))
        assert "FROM rl_rule" in sql
        return self.rows


def _rule(contract: dict[str, object]) -> dict[str, object]:
    return {
        "rule_id": "CM_CO_RULE_QUERY_IDENTIFIER_FEATURE",
        "rule_code": "RL_VERIFIED_SQL_QUERY_IDENTIFIER_FEATURE",
        "remark": json.dumps(contract),
    }


def _contract() -> dict[str, object]:
    return {
        "feature_pattern": "^[A-Z][A-Z0-9_]{2,39}$",
        "forbidden_feature_codes": [
            "SQL",
            "SQL_QUERY",
            "VERIFIED_SQL",
            "VERIFIED_SQL_QUERY",
            "TE_COMMON_CM_VERIFIED_SQL_QUERY",
        ],
    }


def test_resolve_returns_rule_trace_for_semantic_feature_code() -> None:
    database = _RuleDatabase([_rule(_contract())])

    resolution = QueryIdentifierFeatureRuleResolver(database).resolve(
        "read_rule_child_identifier_metadata"
    )

    assert resolution.query_feature_code == "READ_RULE_CHILD_IDENTIFIER_METADATA"
    assert resolution.rule_code == "RL_VERIFIED_SQL_QUERY_IDENTIFIER_FEATURE"
    assert database.calls[0][1] == ("QUERY_IDENTIFIER_FEATURE",)


@pytest.mark.parametrize(
    "query_feature_code",
    (
        "SQL",
        "SQL_QUERY",
        "VERIFIED_SQL",
        "VERIFIED_SQL_QUERY",
        "TE_COMMON_CM_VERIFIED_SQL_QUERY",
    ),
)
def test_resolve_rejects_feature_codes_forbidden_by_rule(
    query_feature_code: str,
) -> None:
    resolver = QueryIdentifierFeatureRuleResolver(
        _RuleDatabase([_rule(_contract())])
    )

    with pytest.raises(ValueError, match="active Rule forbids"):
        resolver.resolve(query_feature_code)


@pytest.mark.parametrize("query_feature_code", ("A", "READ-RULE", "READ RULE"))
def test_resolve_rejects_code_outside_rule_pattern(query_feature_code: str) -> None:
    resolver = QueryIdentifierFeatureRuleResolver(
        _RuleDatabase([_rule(_contract())])
    )

    with pytest.raises(ValueError, match="does not satisfy"):
        resolver.resolve(query_feature_code)


@pytest.mark.parametrize("rows", ([], [_rule(_contract()), _rule(_contract())]))
def test_resolve_requires_exactly_one_active_rule(
    rows: list[dict[str, object]],
) -> None:
    resolver = QueryIdentifierFeatureRuleResolver(_RuleDatabase(rows))

    with pytest.raises(LookupError, match="exactly one active Rule"):
        resolver.resolve("READ_RULE_CHILD_IDENTIFIER_METADATA")
