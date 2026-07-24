"""Rule Action dispatcher: verified_query_id -> Stored Procedure."""

from engine.runtime.action_metadata_repository import ActionMetadataRepository
from engine.runtime.procedure_executor import ProcedureExecutor


class ActionDispatcher:
    def __init__(self, verified_query_reader, procedure_executor=None):
        self.metadata_repository = ActionMetadataRepository(verified_query_reader)
        self.procedure_executor = procedure_executor or ProcedureExecutor()

    def dispatch(self, verified_query_id, parameters):
        verified_query = self.metadata_repository.get_verified_query(verified_query_id)
        result = self.procedure_executor.execute(verified_query, parameters)
        return {
            "verified_query_id": verified_query["verified_query_id"],
            "procedure_name": verified_query["procedure_name"],
            "result": result,
        }
