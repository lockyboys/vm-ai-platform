"""Rule Action Runtime: Rule -> Action Metadata -> Verified Query -> Procedure."""

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
            {
                "rule_action_id": action["rule_action_id"],
                "action_type_code": action["action_type_code"],
                "verified_query_id": action["verified_query_id"],
                "result": self.action_dispatcher.dispatch(
                    action["verified_query_id"],
                    parameters,
                ),
            }
            for action in actions
        ]
