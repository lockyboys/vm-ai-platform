"""Rule Action dispatcher: Action Metadata -> Verified Query -> Stored Procedure."""

from engine.runtime.action_metadata_repository import ActionMetadataRepository
from engine.runtime.procedure_executor import ProcedureExecutor


class ActionDispatcher:
    def __init__(self, metadata_repository=None, procedure_executor=None):
        self.metadata_repository = metadata_repository or ActionMetadataRepository()
        self.procedure_executor = procedure_executor or ProcedureExecutor()

    def dispatch(self, action_code, parameters):
        execution_contract = self.metadata_repository.resolve_execution_contract(action_code)
        verified_query = execution_contract["verified_query"]
        result = self.procedure_executor.execute(verified_query, parameters)
        return {
            "action_code": execution_contract["action_metadata"]["action_code"],
            "verified_query_id": verified_query["verified_query_id"],
            "procedure_name": verified_query["procedure_name"],
            "result": result,
        }
