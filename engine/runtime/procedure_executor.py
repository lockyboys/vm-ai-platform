"""Stored Procedure executor. Procedure names originate only from Repository metadata."""

import json

from common.database import CommonDatabase


class ProcedureExecutor:
    def execute(self, verified_query, parameters):
        self._validate_parameters(verified_query["parameter_definition"], parameters)
        database = CommonDatabase(verified_query["database_role"])
        transaction_required = verified_query.get("transaction_required_yn") == "Y"

        try:
            if transaction_required:
                database.begin()

            with database.connection.cursor() as cursor:
                cursor.callproc(
                    verified_query["procedure_name"],
                    (json.dumps(parameters, ensure_ascii=False),),
                )
                result_sets = []
                while True:
                    rows = cursor.fetchall()
                    if rows:
                        result_sets.append(rows)
                    if not cursor.nextset():
                        break

            if transaction_required:
                database.commit()
            return result_sets[-1] if result_sets else []
        except Exception:
            if transaction_required and verified_query.get("rollback_policy") == "ROLLBACK_ON_ERROR":
                database.rollback()
            raise
        finally:
            database.close()

    @staticmethod
    def _validate_parameters(schema, parameters):
        if not isinstance(parameters, dict):
            raise TypeError("Procedure parameters must be an object.")
        missing = [key for key in schema.get("required", []) if parameters.get(key) is None]
        if missing:
            raise ValueError(f"Required procedure parameters are missing: {', '.join(missing)}")
