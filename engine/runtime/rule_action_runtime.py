"""Rule Action Runtime: Rule -> Action Metadata -> Verified Query -> Procedure."""

from collections.abc import Mapping

from engine.runtime.action_dispatcher import ActionDispatcher
from engine.runtime.procedure_executor import ProcedureExecutor
from repository.common.rule_action_repository import RuleActionRepository
from repository.common.verified_sql_query_repository import VerifiedSqlQueryRepository


class RuleActionRuntime:
    def __init__(self, rule_action_repository, action_dispatcher):
        self.rule_action_repository = rule_action_repository
        self.action_dispatcher = action_dispatcher

    @classmethod
    def from_common_repository(cls, common_database, procedure_executor=None):
        verified_query_repository = VerifiedSqlQueryRepository(common_database)
        action_dispatcher = ActionDispatcher(
            verified_query_reader=verified_query_repository,
            procedure_executor=procedure_executor or ProcedureExecutor(),
        )
        return cls(
            rule_action_repository=RuleActionRepository(common_database),
            action_dispatcher=action_dispatcher,
        )

    def execute(self, rule_id, parameters):
        actions = self.rule_action_repository.get_active_actions(rule_id)
        return [
            self._execute_action_contract(
                action,
                self._build_execution_parameters(
                    rule_id=rule_id,
                    action=action,
                    parameters=parameters,
                ),
            )
            for action in actions
        ]

    def execute_action(self, rule_id, rule_action_id, parameters):
        """Execute only the Rule Action selected by a Rule Resolver."""
        action = self.rule_action_repository.get_active_action(
            rule_id,
            rule_action_id,
        )
        return self._execute_action_contract(
            action,
            self._build_execution_parameters(
                rule_id=rule_id,
                action=action,
                parameters=parameters,
            ),
        )

    @staticmethod
    def _build_execution_parameters(rule_id, action, parameters):
        """Attach Repository-selected Rule identity after untrusted input values."""
        if not isinstance(parameters, Mapping):
            raise TypeError("Rule Action parameters must be an object.")

        execution_context = {
            "rule_id": str(rule_id),
            "rule_action_id": str(action["rule_action_id"]),
            "action_type_code": str(action["action_type_code"]),
        }
        action_type_group_code = action.get("action_type_group_code")
        if action_type_group_code not in (None, ""):
            execution_context["action_type_group_code"] = str(
                action_type_group_code
            )

        return {**dict(parameters), **execution_context}

    def _execute_action_contract(self, action, parameters):
        return {
            "rule_action_id": action["rule_action_id"],
            "action_type_code": action["action_type_code"],
            "verified_query_id": action["verified_query_id"],
            "result": self.action_dispatcher.dispatch(
                action["verified_query_id"],
                parameters,
            ),
        }
