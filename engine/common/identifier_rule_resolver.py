"""SPS Identifier Rule Resolver.

Story:
    Identifier Runtime은 Rule Repository에 등록된 정책만으로 Object Level을
    선택한다. Object metadata는 Rule이 허용한 입력값일 뿐, Level 결정의
    우회 경로가 아니다.

Change History:
    20260802 | OpenAI | rl_rule_action.action_value.condition_id로 Condition과 Action을 1:1 바인딩하고, Object metadata Level 우회 경로를 제거함.
    20260802 | OpenAI | Negative Default Action도 condition_id와 Action 계약의 condition_context로 평가하도록 확장함.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from common.database import CommonDatabase
from engine.runtime.rule_action_runtime import RuleActionRuntime


@dataclass(frozen=True)
class IdentifierRuleResolution:
    """Identifier Runtime이 실제로 적용한 Rule 판단 결과."""

    rule_id: str
    rule_code: str
    rule_action_id: str
    action_type_code: str
    object_level: int
    resolution_source: str


class IdentifierRuleResolver:
    """Rule Repository에서 Identifier Object Level 정책을 해석한다."""

    RULE_GROUP_CODE = "OBJECT_LEVEL"
    TIME_RULE_GROUP_CODE = "IDENTIFIER_TIMEZONE"
    TIME_ACTION_TYPE_CODE = "IDENTIFIER_TIMEZONE_RESOLUTION"

    def __init__(
        self,
        *,
        rule_database: Any | None = None,
        rule_action_runtime: RuleActionRuntime | None = None,
    ) -> None:
        self._rule_database = rule_database
        self._rule_action_runtime = rule_action_runtime

    def resolve_timezone_id(self, rule_context: Mapping[str, Any]) -> str:
        """활성 Identifier 시간 Rule에서 명시 Condition 또는 DEFAULT Timezone을 반환한다."""
        actions = self._load_active_timezone_actions()
        if not actions:
            raise LookupError("Active Identifier Timezone Rule Action not found.")

        candidates = self._select_candidate_actions(
            actions=actions,
            object_metadata=rule_context,
        )
        if not candidates:
            raise LookupError(
                "No active Identifier Timezone Rule matched the runtime context."
            )

        action = candidates[0]
        timezone_id = str(action["contract"].get("timezone_id") or "").strip()
        if not timezone_id:
            raise ValueError(
                "Identifier Timezone Rule Action requires timezone_id. "
                f"rule_action_id={action['rule_action_id']}"
            )
        return timezone_id

    def resolve_object_level(
        self,
        object_metadata: Mapping[str, Any],
    ) -> IdentifierRuleResolution:
        """활성 Object Level Rule을 평가하여 Identifier Blueprint Level을 반환한다."""
        rule_context = self._build_rule_context(object_metadata)
        actions = self._load_active_object_level_actions()
        if not actions:
            raise LookupError(
                "Active Identifier Object Level Rule Action not found."
            )

        for action in self._select_candidate_actions(
            actions=actions,
            object_metadata=rule_context,
        ):

            # Rule Group 전체의 EXPLICIT_RULE을 먼저 평가한 뒤,
            # 일치하는 명시 Action이 없을 때만 DEFAULT를 적용한다.
            for resolution_source in self._normalized_resolution_order(
                action["contract"]
            ):
                if resolution_source == "EXPLICIT_RULE":
                    explicit_level = self._resolve_explicit_level(
                        contract=action["contract"],
                    )
                    if explicit_level is not None:
                        return self._build_resolution(
                            action=action,
                            object_level=explicit_level,
                            resolution_source=resolution_source,
                        )
                elif resolution_source == "DEFAULT":
                    if not self._has_default_level(action["contract"]):
                        continue
                    default_level = self._resolve_default_level(
                        action=action,
                        object_metadata=rule_context,
                    )
                    return self._build_resolution(
                        action=action,
                        object_level=default_level,
                        resolution_source="DEFAULT",
                    )

        raise LookupError(
            "No active Identifier Object Level Rule matched the Object metadata. "
            f"object_code={rule_context.get('object_code')}"
        )

    def _load_active_object_level_actions(self) -> list[dict[str, Any]]:
        rows = self._get_rule_database().fetch_all(
            """
            SELECT
                r.rule_id,
                r.rule_code,
                r.priority_no,
                r.sort_no AS rule_sort_no,
                a.rule_action_id,
                a.action_type_code,
                a.action_value,
                a.sort_no AS action_sort_no,
                c.common_code_json AS action_type_contract_json
            FROM rl_rule r
            JOIN rl_rule_action a
              ON a.rule_id = r.rule_id
             AND a.status_code = 'ACTIVE'
             AND a.deleted_dt IS NULL
            JOIN cm_common_code c
              ON c.group_code = 'ACTION_TYPE'
             AND c.code = a.action_type_code
             AND c.status_code = 'ACTIVE'
             AND c.deleted_dt IS NULL
            WHERE r.rule_group_code = %s
              AND r.status_code = 'ACTIVE'
              AND r.deleted_dt IS NULL
            ORDER BY
                r.priority_no DESC,
                r.sort_no,
                a.sort_no,
                a.rule_action_id
            """,
            (self.RULE_GROUP_CODE,),
        )

        actions: list[dict[str, Any]] = []
        condition_cache: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            action_type_contract = self._load_optional_contract(
                row.get("action_type_contract_json"),
                label=(
                    "ACTION_TYPE common-code contract "
                    f"action_type_code={row.get('action_type_code')}"
                ),
            )
            action_contract = self._load_optional_contract(
                row.get("action_value"),
                label=(
                    "Rule Action contract "
                    f"rule_action_id={row.get('rule_action_id')}"
                ),
            )
            contract = {**action_type_contract, **action_contract}
            if not self._is_object_level_contract(contract):
                continue

            rule_id = str(row["rule_id"])
            if rule_id not in condition_cache:
                condition_cache[rule_id] = self._load_active_conditions(rule_id)

            condition_id = self._extract_action_condition_id(
                contract=contract,
                rule_action_id=str(row["rule_action_id"]),
            )
            resolution_order = self._normalized_resolution_order(contract)
            if condition_id is None:
                if "DEFAULT" not in resolution_order:
                    raise ValueError(
                        "Rule Action without condition_id must declare DEFAULT resolution. "
                        f"rule_action_id={row['rule_action_id']}"
                    )
                if contract.get("object_level") not in (None, ""):
                    raise ValueError(
                        "Rule Action object_level requires condition_id binding. "
                        f"rule_action_id={row['rule_action_id']}"
                    )
            elif (
                len(resolution_order) != 1
                or resolution_order[0] not in {"EXPLICIT_RULE", "DEFAULT"}
            ):
                raise ValueError(
                    "Condition-bound Rule Action must declare exactly one supported resolution. "
                    f"rule_action_id={row['rule_action_id']}"
                )

            actions.append(
                {
                    **dict(row),
                    "contract": contract,
                    "condition_id": condition_id,
                    "conditions": self._bind_action_conditions(
                        rule_id=rule_id,
                        rule_action_id=str(row["rule_action_id"]),
                        condition_id=condition_id,
                        conditions=condition_cache[rule_id],
                    ),
                }
            )
        return actions

    def _load_active_timezone_actions(self) -> list[dict[str, Any]]:
        rows = self._get_rule_database().fetch_all(
            """
            SELECT
                r.rule_id,
                r.rule_code,
                r.priority_no,
                r.sort_no AS rule_sort_no,
                a.rule_action_id,
                a.action_type_code,
                a.action_value,
                a.sort_no AS action_sort_no,
                t.common_code_json AS action_type_contract_json,
                c.condition_id,
                c.field_code,
                c.operator_code,
                c.condition_value,
                c.logical_operator_code,
                c.sort_no AS condition_sort_no
            FROM rl_rule r
            JOIN rl_rule_action a
              ON a.rule_id = r.rule_id
             AND a.action_type_code = %s
             AND a.status_code = 'ACTIVE'
             AND a.deleted_dt IS NULL
            JOIN cm_common_code t
              ON t.group_code = 'ACTION_TYPE'
             AND t.code = a.action_type_code
             AND t.status_code = 'ACTIVE'
             AND t.deleted_dt IS NULL
            LEFT JOIN rl_rule_condition c
              ON c.condition_id = JSON_UNQUOTE(
                     JSON_EXTRACT(a.action_value, '$.condition_id')
                 )
             AND c.rule_id = r.rule_id
             AND c.status_code = 'ACTIVE'
             AND c.deleted_dt IS NULL
            WHERE r.rule_group_code = %s
              AND r.status_code = 'ACTIVE'
              AND r.deleted_dt IS NULL
            ORDER BY
                r.priority_no DESC,
                r.sort_no,
                a.sort_no,
                a.rule_action_id
            """,
            (self.TIME_ACTION_TYPE_CODE, self.TIME_RULE_GROUP_CODE),
        )

        actions: list[dict[str, Any]] = []
        for row in rows:
            action_type_contract = self._load_optional_contract(
                row.get("action_type_contract_json"),
                label=(
                    "ACTION_TYPE common-code contract "
                    f"action_type_code={row.get('action_type_code')}"
                ),
            )
            action_contract = self._load_optional_contract(
                row.get("action_value"),
                label=(
                    "Rule Action contract "
                    f"rule_action_id={row.get('rule_action_id')}"
                ),
            )
            contract = {**action_type_contract, **action_contract}
            condition_id = self._extract_action_condition_id(
                contract=contract,
                rule_action_id=str(row["rule_action_id"]),
            )
            conditions = []
            if condition_id is not None:
                if str(row.get("condition_id") or "").strip() != condition_id:
                    raise LookupError(
                        "Timezone Rule Action condition_id must reference one active Condition. "
                        f"rule_action_id={row['rule_action_id']}"
                    )
                conditions = [
                    {
                        "condition_id": condition_id,
                        "field_code": row["field_code"],
                        "operator_code": row["operator_code"],
                        "condition_value": row.get("condition_value"),
                        "logical_operator_code": row.get("logical_operator_code"),
                        "sort_no": row.get("condition_sort_no"),
                    }
                ]
            actions.append(
                {
                    **dict(row),
                    "contract": contract,
                    "condition_id": condition_id,
                    "conditions": conditions,
                }
            )
        return actions

    def _load_active_conditions(self, rule_id: str) -> list[dict[str, Any]]:
        return list(
            self._get_rule_database().fetch_all(
                """
                SELECT
                    condition_id,
                    field_code,
                    operator_code,
                    condition_value,
                    logical_operator_code,
                    sort_no
                FROM rl_rule_condition
                WHERE rule_id = %s
                  AND status_code = 'ACTIVE'
                  AND deleted_dt IS NULL
                ORDER BY sort_no, condition_id
                """,
                (rule_id,),
            )
        )

    @staticmethod
    def _build_rule_context(object_metadata: Mapping[str, Any]) -> dict[str, Any]:
        return {
            field_name: value
            for field_name, value in object_metadata.items()
            if str(field_name).strip().casefold() != "object_level"
        }

    @staticmethod
    def _extract_action_condition_id(
        *,
        contract: Mapping[str, Any],
        rule_action_id: str,
    ) -> str | None:
        if "condition_id" not in contract:
            return None

        condition_id = str(contract["condition_id"]).strip()
        if not condition_id:
            raise ValueError(
                "Rule Action condition_id must not be blank. "
                f"rule_action_id={rule_action_id}"
            )
        return condition_id

    @staticmethod
    def _bind_action_conditions(
        *,
        rule_id: str,
        rule_action_id: str,
        condition_id: str | None,
        conditions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if condition_id is None:
            return []

        bound_conditions = [
            condition
            for condition in conditions
            if str(condition.get("condition_id") or "").strip() == condition_id
        ]
        if len(bound_conditions) != 1:
            raise LookupError(
                "Rule Action condition_id must reference exactly one active Rule Condition. "
                f"rule_id={rule_id}, rule_action_id={rule_action_id}, "
                f"condition_id={condition_id}"
            )
        return bound_conditions

    @staticmethod
    def _is_object_level_contract(contract: Mapping[str, Any]) -> bool:
        resolution_order = contract.get("resolution_order")
        return isinstance(resolution_order, list) and bool(resolution_order)

    @staticmethod
    def _normalized_resolution_order(contract: Mapping[str, Any]) -> list[str]:
        resolution_order = contract.get("resolution_order")
        if not isinstance(resolution_order, list) or not resolution_order:
            raise ValueError(
                "Identifier Rule Action requires a non-empty resolution_order."
            )
        normalized = [
            str(source).strip().upper()
            for source in resolution_order
            if str(source).strip()
        ]
        unsupported = set(normalized) - {"EXPLICIT_RULE", "DEFAULT"}
        if unsupported:
            raise ValueError(
                "Unsupported Identifier Rule resolution source. "
                f"sources={sorted(unsupported)}"
            )
        return normalized

    def _select_candidate_actions(
        self,
        *,
        actions: list[dict[str, Any]],
        object_metadata: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        actions_by_rule_id: dict[str, list[dict[str, Any]]] = {}
        for action in actions:
            rule_id = str(action["rule_id"])
            actions_by_rule_id.setdefault(rule_id, []).append(action)

        for rule_actions in actions_by_rule_id.values():
            matched_actions = [
                action
                for action in rule_actions
                if (
                    action["condition_id"] is not None
                    and "EXPLICIT_RULE"
                    in self._normalized_resolution_order(action["contract"])
                    and self._matches_conditions(
                        conditions=action["conditions"],
                        object_metadata=self._build_action_condition_context(
                            object_metadata=object_metadata,
                            action=action,
                        ),
                    )
                )
            ]
            if len(matched_actions) > 1:
                action_ids = [
                    str(action["rule_action_id"])
                    for action in matched_actions
                ]
                raise LookupError(
                    "Identifier Rule matched multiple condition-bound Actions. "
                    f"rule_id={rule_actions[0]['rule_id']}, "
                    f"rule_action_ids={action_ids}"
                )
            if matched_actions:
                return matched_actions

        for rule_actions in actions_by_rule_id.values():
            default_actions = [
                action
                for action in rule_actions
                if "DEFAULT" in self._normalized_resolution_order(action["contract"])
            ]
            matched_default_actions = [
                action
                for action in default_actions
                if (
                    action["condition_id"] is None
                    or self._matches_conditions(
                        conditions=action["conditions"],
                        object_metadata=self._build_action_condition_context(
                            object_metadata={
                                **object_metadata,
                                "rule_resolution_source": "DEFAULT",
                            },
                            action=action,
                        ),
                    )
                )
            ]
            if len(matched_default_actions) > 1:
                action_ids = [
                    str(action["rule_action_id"])
                    for action in matched_default_actions
                ]
                raise LookupError(
                    "Identifier Rule matched multiple Default Actions. "
                    f"rule_id={rule_actions[0]['rule_id']}, "
                    f"rule_action_ids={action_ids}"
                )
            if matched_default_actions:
                return matched_default_actions

        return []

    @classmethod
    def _build_action_condition_context(
        cls,
        *,
        object_metadata: Mapping[str, Any],
        action: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Action 계약이 제공한 평가 컨텍스트만 현재 Rule Context에 합친다."""
        context = dict(object_metadata)
        raw_condition_context = action["contract"].get("condition_context")
        if raw_condition_context in (None, ""):
            return context
        if not isinstance(raw_condition_context, Mapping):
            raise ValueError(
                "Rule Action condition_context must be a JSON object. "
                f"rule_action_id={action['rule_action_id']}"
            )

        for field_code, value in raw_condition_context.items():
            if not isinstance(field_code, str) or not field_code.strip():
                raise ValueError(
                    "Rule Action condition_context field code must be a non-empty string. "
                    f"rule_action_id={action['rule_action_id']}"
                )
            normalized_field_code = field_code.strip()
            existing_field_names = [
                field_name
                for field_name in context
                if str(field_name).strip().casefold()
                == normalized_field_code.casefold()
            ]
            if existing_field_names:
                existing_value = context[existing_field_names[0]]
                if cls._normalize_value(existing_value) != cls._normalize_value(value):
                    raise ValueError(
                        "Rule Action condition_context must not override Object metadata. "
                        f"rule_action_id={action['rule_action_id']}, "
                        f"field_code={normalized_field_code}"
                    )
                continue
            context[normalized_field_code] = value
        return context

    def _matches_conditions(
        self,
        *,
        conditions: list[dict[str, Any]],
        object_metadata: Mapping[str, Any],
    ) -> bool:
        if not conditions:
            return True

        combined: bool | None = None
        for condition in conditions:
            result = self._evaluate_condition(
                condition=condition,
                object_metadata=object_metadata,
            )
            if combined is None:
                combined = result
                continue

            logical_operator = str(
                condition.get("logical_operator_code") or "AND"
            ).strip().upper()
            if logical_operator == "AND":
                combined = combined and result
            elif logical_operator == "OR":
                combined = combined or result
            else:
                raise ValueError(
                    "Unsupported Rule logical operator. "
                    f"condition_id={condition.get('condition_id')}, "
                    f"logical_operator_code={logical_operator}"
                )
        return bool(combined)

    def _evaluate_condition(
        self,
        *,
        condition: Mapping[str, Any],
        object_metadata: Mapping[str, Any],
    ) -> bool:
        field_code = str(condition["field_code"]).strip()
        actual_value = self._find_context_value(object_metadata, field_code)
        expected_value = condition.get("condition_value")
        operator_code = str(condition["operator_code"]).strip().upper()

        if operator_code == "IS_NULL":
            return actual_value in (None, "")
        if operator_code == "NOT_NULL":
            return actual_value not in (None, "")

        if operator_code in {"IN", "NOT_IN"}:
            expected_values = self._load_expected_values(expected_value)
            matched = self._normalize_value(actual_value) in {
                self._normalize_value(value) for value in expected_values
            }
            return matched if operator_code == "IN" else not matched

        if operator_code in {"EQ", "NE"}:
            matched = self._normalize_value(actual_value) == self._normalize_value(
                expected_value
            )
            return matched if operator_code == "EQ" else not matched

        if operator_code in {"GT", "GE", "LT", "LE"}:
            actual_number = self._as_number(actual_value, condition)
            expected_number = self._as_number(expected_value, condition)
            if operator_code == "GT":
                return actual_number > expected_number
            if operator_code == "GE":
                return actual_number >= expected_number
            if operator_code == "LT":
                return actual_number < expected_number
            return actual_number <= expected_number

        raise ValueError(
            "Unsupported Rule condition operator. "
            f"condition_id={condition.get('condition_id')}, "
            f"operator_code={operator_code}"
        )

    @staticmethod
    def _find_context_value(
        object_metadata: Mapping[str, Any],
        field_code: str,
    ) -> Any:
        normalized_field_code = field_code.strip().upper()
        for field_name, value in object_metadata.items():
            if str(field_name).strip().upper() == normalized_field_code:
                return value
        return None

    @staticmethod
    def _load_expected_values(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            normalized_value = value.strip()
            if normalized_value.startswith("["):
                try:
                    parsed = json.loads(normalized_value)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        "Rule IN condition value must be valid JSON array."
                    ) from error
                if not isinstance(parsed, list):
                    raise ValueError(
                        "Rule IN condition value must be a JSON array."
                    )
                return parsed
            return [item.strip() for item in normalized_value.split(",")]
        return [value]

    @staticmethod
    def _normalize_value(value: Any) -> str:
        return "" if value is None else str(value).strip().casefold()

    @staticmethod
    def _as_number(
        value: Any,
        condition: Mapping[str, Any],
    ) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Numeric Rule condition requires numeric values. "
                f"condition_id={condition.get('condition_id')}"
            ) from error

    @staticmethod
    def _resolve_explicit_level(
        *,
        contract: Mapping[str, Any],
    ) -> int | None:
        if contract.get("object_level") not in (None, ""):
            return IdentifierRuleResolver._as_object_level(
                contract["object_level"],
                "Rule Action object_level",
            )
        return None

    def _resolve_default_level(
        self,
        *,
        action: Mapping[str, Any],
        object_metadata: Mapping[str, Any],
    ) -> int:
        contract = action["contract"]
        contract_default = self._as_object_level(
            contract.get("default_object_level"),
            "Rule Action default_object_level",
        )
        verified_query_id = contract.get("verified_query_id")
        if not verified_query_id:
            return contract_default

        procedure_default = self._execute_default_action(
            action=action,
            object_metadata=object_metadata,
        )
        if procedure_default != contract_default:
            raise ValueError(
                "Rule Action default Object Level does not match Procedure result. "
                f"rule_action_id={action['rule_action_id']}, "
                f"contract_default={contract_default}, "
                f"procedure_default={procedure_default}"
            )
        return procedure_default

    def _execute_default_action(
        self,
        *,
        action: Mapping[str, Any],
        object_metadata: Mapping[str, Any],
    ) -> int:
        selected = self._get_rule_action_runtime().execute_action(
            action["rule_id"],
            action["rule_action_id"],
            dict(object_metadata),
        )
        if not isinstance(selected, Mapping):
            raise ValueError(
                "Selected Identifier Rule Action execution result is invalid. "
                f"rule_action_id={action['rule_action_id']}"
            )

        dispatch_result = selected.get("result")
        if not isinstance(dispatch_result, Mapping):
            raise ValueError(
                "Identifier Rule Action execution result is invalid. "
                f"rule_action_id={action['rule_action_id']}"
            )
        rows = dispatch_result.get("result")
        if not isinstance(rows, list) or not rows:
            raise ValueError(
                "Identifier Rule Action Procedure returned no result. "
                f"rule_action_id={action['rule_action_id']}"
            )
        row = rows[0]
        if not isinstance(row, Mapping):
            raise ValueError(
                "Identifier Rule Action Procedure result must be an object. "
                f"rule_action_id={action['rule_action_id']}"
            )
        self._assert_procedure_identity(action=action, row=row)
        return self._as_object_level(
            row.get("default_object_level"),
            "Rule Action Procedure default_object_level",
        )

    @staticmethod
    def _assert_procedure_identity(
        *,
        action: Mapping[str, Any],
        row: Mapping[str, Any],
    ) -> None:
        expected_rule_id = str(action["rule_id"]).strip()
        expected_rule_code = str(action["rule_code"]).strip()
        actual_rule_id = str(row.get("rule_id") or "").strip()
        actual_rule_code = str(row.get("rule_code") or "").strip()
        actual_rule_action_id = str(row.get("rule_action_id") or "").strip()
        actual_action_type_code = str(row.get("action_type_code") or "").strip()
        actual_resolution_source = str(
            row.get("resolution_source") or ""
        ).strip().upper()

        if (
            actual_rule_id != expected_rule_id
            or actual_rule_code != expected_rule_code
            or actual_rule_action_id != str(action["rule_action_id"]).strip()
            or actual_action_type_code != str(action["action_type_code"]).strip()
        ):
            raise ValueError(
                "Identifier Rule Action Procedure resolved a different Rule. "
                f"rule_action_id={action['rule_action_id']}, "
                f"expected_rule_id={expected_rule_id}, "
                f"actual_rule_id={actual_rule_id}, "
                f"expected_rule_code={expected_rule_code}, "
                f"actual_rule_code={actual_rule_code}, "
                f"expected_rule_action_id={action['rule_action_id']}, "
                f"actual_rule_action_id={actual_rule_action_id}, "
                f"expected_action_type_code={action['action_type_code']}, "
                f"actual_action_type_code={actual_action_type_code}"
            )
        if actual_resolution_source != "DEFAULT":
            raise ValueError(
                "Identifier Rule Action Procedure returned an invalid resolution source. "
                f"rule_action_id={action['rule_action_id']}, "
                f"resolution_source={actual_resolution_source}"
            )

    @staticmethod
    def _has_default_level(contract: Mapping[str, Any]) -> bool:
        return contract.get("default_object_level") not in (None, "")

    @staticmethod
    def _build_resolution(
        *,
        action: Mapping[str, Any],
        object_level: int,
        resolution_source: str,
    ) -> IdentifierRuleResolution:
        return IdentifierRuleResolution(
            rule_id=str(action["rule_id"]),
            rule_code=str(action["rule_code"]),
            rule_action_id=str(action["rule_action_id"]),
            action_type_code=str(action["action_type_code"]),
            object_level=object_level,
            resolution_source=resolution_source,
        )

    def _resolve_identifier_timezone_id(
        self,
        contract: Mapping[str, Any],
    ) -> str | None:
        locale_group_code = str(
            contract.get("identifier_locale_group_code") or ""
        ).strip()
        locale_code = str(contract.get("identifier_locale_code") or "").strip()
        if not locale_group_code and not locale_code:
            return None
        if not locale_group_code or not locale_code:
            raise ValueError(
                "Identifier timezone Rule requires both locale group and code."
            )

        cache_key = (locale_group_code, locale_code)
        if cache_key in self._timezone_cache:
            return self._timezone_cache[cache_key]

        row = self._get_rule_database().fetch_one(
            """
            SELECT JSON_UNQUOTE(
                       JSON_EXTRACT(common_code_json, '$.timezone_id')
                   ) AS timezone_id
            FROM cm_common_code
            WHERE group_code = %s
              AND code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            """,
            cache_key,
        )
        timezone_id = str((row or {}).get("timezone_id") or "").strip()
        if not timezone_id:
            raise LookupError(
                "Identifier timezone Locale metadata not found. "
                f"group_code={locale_group_code}, code={locale_code}"
            )
        self._timezone_cache[cache_key] = timezone_id
        return timezone_id

    @staticmethod
    def _as_object_level(value: Any, field_name: str) -> int:
        try:
            object_level = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{field_name} must be an integer. value={value!r}"
            ) from error
        if object_level <= 0:
            raise ValueError(
                f"{field_name} must be positive. value={object_level}"
            )
        return object_level

    @staticmethod
    def _load_optional_contract(value: Any, *, label: str) -> dict[str, Any]:
        if value in (None, ""):
            return {}
        if isinstance(value, Mapping):
            return dict(value)
        try:
            parsed = json.loads(str(value))
        except json.JSONDecodeError as error:
            raise ValueError(
                f"{label} must be valid JSON."
            ) from error
        if not isinstance(parsed, dict):
            raise ValueError(f"{label} must be a JSON object.")
        return parsed

    def _get_rule_database(self) -> Any:
        if self._rule_database is None:
            self._rule_database = CommonDatabase(database_role="COMMON")
        return self._rule_database

    def _get_rule_action_runtime(self) -> RuleActionRuntime:
        if self._rule_action_runtime is None:
            self._rule_action_runtime = RuleActionRuntime.from_common_repository(
                self._get_rule_database()
            )
        return self._rule_action_runtime
