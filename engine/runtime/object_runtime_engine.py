from datetime import datetime


class ObjectRuntimeLogger:
    """
    Object Runtime Engine Logger
    """

    def __init__(self):
        self.engine_name = "Object Runtime Engine"

    def header(self):
        print("=" * 70)
        print(self.engine_name)
        print("=" * 70)

    def step(self, step_no, title, status="OK"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{now}]")
        print(f"[STEP-{step_no:03d}] {title}")
        print(f"STATUS : {status}")
        print("-" * 70)

    def info(self, key, value):
        print(f"{key:<25}: {value}")

    def footer(self):
        print("=" * 70)


class ObjectRuntimeEngine:
    """
    Object Runtime Engine Prototype

    STEP-001
        Execution Request

    STEP-002
        Load Object Metadata

    STEP-003
        Build Execution Plan
    """

    #################################################################
    # Generate Identifier
    #################################################################

    def _generate_identifier(self, object_metadata):

        identifier_target_code = object_metadata["identifier_target_code"]

        # Prototype
        generated_identifier = f"{identifier_target_code}_20260706_00001"

        return {
            "identifier_target_code": identifier_target_code,
            "generated_identifier": generated_identifier
        }

    def __init__(self):

        self.logger = ObjectRuntimeLogger()

    #################################################################
    # Execute
    #################################################################

    def execute(self, object_code: str):

        self.logger.header()

        #############################################################
        # STEP-001
        #############################################################

        self.logger.step(1, "Execution Request")

        self.logger.info("Object Code", object_code)


        #############################################################
        # STEP-002
        #############################################################
        try:

            object_metadata = self._load_object_metadata(object_code)

        except Exception as ex:

            self.logger.step(2, "Load Object Metadata", "FAILED")
            self.logger.info("Message", str(ex))
            self.logger.footer()

            return {
                "success": False,
                "message": str(ex)
            }        
        #object_metadata = self._load_object_metadata(object_code)

        self.logger.step(2, "Load Object Metadata")

        self.logger.info("Object ID", object_metadata["object_id"])
        self.logger.info("Object Code", object_metadata["object_code"])
        self.logger.info("Object Name", object_metadata["object_name"])
        self.logger.info(
            "Identifier Target",
            object_metadata["identifier_target_code"]
        )

        #############################################################
        # STEP-003
        #############################################################

        execution_plan = self._build_execution_plan(object_metadata)

        self.logger.step(3, "Build Execution Plan")

        for plan in execution_plan:

            self.logger.info(
                f"STEP-{plan['step_no']:03d}",
                plan["step_name"]
            )

        #############################################################
        # STEP-004
        #############################################################

        identifier_result = self._generate_identifier(object_metadata)

        self.logger.step(4, "Generate Identifier")

        self.logger.info(
            "Identifier Target",
            identifier_result["identifier_target_code"]
        )

        self.logger.info(
            "Generated Identifier",
            identifier_result["generated_identifier"]
        )

        #############################################################
        # STEP-005
        #############################################################

        repository_save_request = self._build_repository_save_request(
            object_metadata,
            identifier_result
        )

        self.logger.step(5, "Build Repository Save Request")

        self.logger.info(
            "Object ID",
            repository_save_request["object_id"]
        )

        self.logger.info(
            "Object Code",
            repository_save_request["object_code"]
        )

        self.logger.info(
            "Identifier",
            repository_save_request["identifier"]
        )

        self.logger.info(
            "Save Status",
            repository_save_request["save_status"]
        )
        #############################################################
        return {
            "status": "SUCCESS",
            "object_code": object_code,
            "object_metadata": object_metadata,
            "execution_plan": execution_plan,
            "identifier_result": identifier_result,
            "repository_save_request": repository_save_request
        }
        # return {
        #     "status": "SUCCESS",
        #     "object_code": object_code,
        #     "object_metadata": object_metadata,
        #     "execution_plan": execution_plan,
        #     "identifier_result": identifier_result
        # }

        # return {
        #     "status": "READY",
        #     "object_code": object_code,
        #     "object_metadata": object_metadata,
        #     "execution_plan": execution_plan
        # }

    #################################################################
    # Load Object Metadata
    #################################################################

    def _load_object_metadata(self, object_code: str):

        repository_mock = {

            "DOCUMENT": {

                "object_id": "OB_20260706_00001",
                "object_code": "DOCUMENT",
                "object_name": "Document Object",
                "identifier_target_code": "DC"

            },

            "BOOK": {

                "object_id": "OB_20260706_00002",
                "object_code": "BOOK",
                "object_name": "Book Object",
                "identifier_target_code": "OB"

            }

        }

        if object_code not in repository_mock:

            raise Exception(f"{object_code} Object not found.")

        return repository_mock[object_code]

    #################################################################
    # Build Execution Plan
    #################################################################

    def _build_execution_plan(self, object_metadata):

        execution_plan = [

            {
                "step_no": 1,
                "step_code": "LOAD_OBJECT_METADATA",
                "step_name": "Load Object Metadata"
            },

            {
                "step_no": 2,
                "step_code": "GENERATE_IDENTIFIER",
                "step_name": "Generate Identifier"
            },

            {
                "step_no": 3,
                "step_code": "SAVE_REPOSITORY",
                "step_name": "Save Repository"
            },

            {
                "step_no": 4,
                "step_code": "SAVE_MONGODB",
                "step_name": "Save MongoDB"
            },

            {
                "step_no": 5,
                "step_code": "SAVE_EXECUTION_LINK",
                "step_name": "Save Execution Link"
            }

        ]

        return execution_plan


    #################################################################
    # Build Repository Save Request
    #################################################################

    def _build_repository_save_request(
        self,
        object_metadata,
        identifier_result
    ):
        """
        Repository 저장 요청 생성

        Prototype
        실제 저장는 하지 않는다.
        """

        repository_save_request = {

            "object_id": object_metadata["object_id"],

            "object_code": object_metadata["object_code"],

            "identifier": identifier_result["generated_identifier"],

            "identifier_target_code":
                identifier_result["identifier_target_code"],

            "save_status": "READY"

        }

        return repository_save_request

#########################################################################
# Main
#########################################################################

if __name__ == "__main__":

    engine = ObjectRuntimeEngine()

    object_code = input("Object Code : ").strip().upper()

    result = engine.execute(object_code)

    print()
    print("=" * 70)
    print("Execution Result")
    print("=" * 70)
    print(result)