"""Resolve the Verified SQL Query-ID feature policy from the Rule Repository."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from common.common_function import normalize_required_text
from common.database import CommonDatabase


@dataclass(frozen=True)
class QueryIdentifierFeatureResolution:
    query_feature_code: str
    rule_id: str
    rule_code: str


class QueryIdentifierFeatureRuleResolver:
    """Validate Query-ID feature codes only against the active Rule contract."""

    RULE_GROUP_CODE = "QUERY_IDENTIFIER_FEATURE"

    def __init__(self, database: CommonDatabase) -> None:
        self.database = database

    def resolve(self, query_feature_code: str) -> QueryIdentifierFeatureResolution:
        normalized = normalize_required_text(
            query_feature_code,
            "query_feature_code",
        ).upper()
        rule = self._load_rule()
        contract = self._load_contract(rule["remark"])

        raw_pattern = normalize_required_text(
            contract.get("feature_pattern"),
            "Query Identifier Feature Rule feature_pattern",
        )
        try:
            feature_pattern = re.compile(raw_pattern)
        except re.error as error:
            raise ValueError(
                "Query Identifier Feature Rule feature_pattern is invalid."
            ) from error
        if feature_pattern.fullmatch(normalized) is None:
            raise ValueError(
                "query_feature_code does not satisfy the active "
                "Query Identifier Feature Rule."
            )

        forbidden_codes = self._normalize_forbidden_codes(
            contract.get("forbidden_feature_codes")
        )
        if normalized in forbidden_codes:
            raise ValueError(
                "query_feature_code must describe the SQL purpose; "
                f"the active Rule forbids: {normalized}"
            )

        return QueryIdentifierFeatureResolution(
            query_feature_code=normalized,
            rule_id=str(rule["rule_id"]),
            rule_code=str(rule["rule_code"]),
        )

    def _load_rule(self) -> dict[str, Any]:
        rows = self.database.fetch_all(
            """
            SELECT
                rule_id,
                rule_code,
                remark
            FROM rl_rule
            WHERE rule_group_code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY priority_no DESC, sort_no, rule_id
            """,
            (self.RULE_GROUP_CODE,),
        )
        if len(rows) != 1:
            raise LookupError(
                "Query Identifier Feature Rule must resolve exactly one active Rule. "
                f"rule_count={len(rows)}"
            )
        return dict(rows[0])

    @staticmethod
    def _load_contract(value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            contract = dict(value)
        else:
            try:
                contract = json.loads(str(value))
            except json.JSONDecodeError as error:
                raise ValueError(
                    "Query Identifier Feature Rule remark must be valid JSON."
                ) from error
        if not isinstance(contract, dict):
            raise ValueError(
                "Query Identifier Feature Rule remark must be a JSON object."
            )
        return contract

    @staticmethod
    def _normalize_forbidden_codes(value: Any) -> set[str]:
        if not isinstance(value, list) or not value:
            raise ValueError(
                "Query Identifier Feature Rule must define forbidden_feature_codes."
            )
        normalized: set[str] = set()
        for item in value:
            code = normalize_required_text(
                item,
                "forbidden_feature_codes item",
            ).upper()
            normalized.add(code)
        return normalized
