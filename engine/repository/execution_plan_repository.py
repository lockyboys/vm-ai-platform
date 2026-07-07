class ExecutionPlanRepository:
    """
    Execution Plan Repository Prototype

    현재는 Mock Repository.
    이후 sp_engine / sp_engine_step 테이블에서 읽도록 전환한다.
    """

    def load_execution_plan(self, engine_code):

        repository_mock = {
            "OBJECT_RUNTIME_ENGINE": [
                {"step_no": 1, "step_code": "LOAD_OBJECT_METADATA", "step_name": "Load Object Metadata"},
                { "step_no": 2, "step_code": "BUILD_EXECUTION_PLAN", "step_name": "Build Execution Plan"},
                {"step_no": 3, "step_code": "PRE_IDENTITY_INTELLIGENCE", "step_name": "Pre-Identity Intelligence"},
                {"step_no": 4, "step_code": "GENERATE_IDENTIFIER", "step_name": "Generate Identifier"},
                {"step_no": 5, "step_code": "BUILD_REPOSITORY_SAVE_REQUEST", "step_name": "Build Repository Save Request"},
                {"step_no": 6, "step_code": "REPOSITORY_GENERATOR_SAVE", "step_name": "Repository Generator Save"},
                {"step_no": 7, "step_code": "BUILD_MONGODB_SAVE_REQUEST", "step_name": "Build MongoDB Save Request"},
                {"step_no": 8, "step_code": "REPOSITORY_INTELLIGENCE",  "step_name": "Repository Intelligence"},
                {"step_no": 9, "step_code": "BUILD_EXECUTION_HISTORY_REQUEST", "step_name": "Build Execution History Request"},
                {"step_no": 10, "step_code": "EXECUTION_HISTORY_GENERATOR_SAVE", "step_name": "Execution History Generator Save"},
                {"step_no": 11, "step_code": "MONGODB_COLLECTION_GENERATOR_SAVE", "step_name": "Build MongoDB Collection Request"},
                {"step_no": 12, "step_code": "SAVE_MONGODB_COLLECTION", "step_name": "Save MongoDB Collection"}
            ]
        }

        if engine_code not in repository_mock:
            raise Exception(f"{engine_code} Execution Plan not found.")

        return repository_mock[engine_code]