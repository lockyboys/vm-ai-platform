import os
from dotenv import load_dotenv
from engine.generator.repository_generator import RepositoryGenerator
from datetime import datetime
from difflib import get_close_matches
from difflib import get_close_matches
from engine.intelligence.ai_engine import AIEngine
from engine.generator.execution_history_generator import ExecutionHistoryGenerator
from engine.generator.mongodb_collection_generator import MongoDBCollectionGenerator
from engine.intelligence.pre_identity_intelligence import PreIdentityIntelligence
from common.database import CommonDatabase
from engine.generator.file_storage_generator import FileStorageGenerator
from engine.generator.mongodb_document_generator import (
    MongoDBDocumentGenerator,
)
from engine.generator.knowledge_document_generator import KnowledgeDocumentGenerator
from engine.identifier_engine import IdentifierEngine
from engine.identifier.coordinator import IdentifierCoordinator

class ObjectRuntimeIntelligence:

    def __init__(self):

        load_dotenv()

        self.google_api_key = os.getenv("GOOGLE_API_KEY")

    def has_api_key(self):

        return self.google_api_key is not None

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
    def __init__(self):
        
        self.database = CommonDatabase(
            database_role="STORY_PLATFORM"
        )

        self.identifier_engine = IdentifierEngine(
            database_manager=self.database
        )
        self.identifier_coordinator = IdentifierCoordinator(
            self.database
        )
        self.logger = ObjectRuntimeLogger()
        self.pre_identity_intelligence = PreIdentityIntelligence()
        self.ai_engine = AIEngine()
        self.execution_history_generator = ExecutionHistoryGenerator()
        self.mongodb_collection_generator = MongoDBCollectionGenerator()
        self.mongodb_document_generator = MongoDBDocumentGenerator()
        self.knowledge_document_generator = KnowledgeDocumentGenerator()
    #################################################################
    # Generate Identifier
    #################################################################

    def _generate_identifier(
        self,
        object_metadata: dict,
    ) -> dict:
        identifier_request = {
            **object_metadata,
        }
        prepared = self.identifier_coordinator.prepare(
            request=identifier_request,
        )
        lock_acquired = False

        self.database.begin()
        try:
            self.identifier_coordinator.acquire(prepared)
            lock_acquired = True
            resolution = self.identifier_coordinator.resolve(
                request=identifier_request,
                prepared=prepared,
            )
            self.database.commit()
        except Exception:
            self.database.rollback()
            raise
        finally:
            if lock_acquired:
                self.identifier_coordinator.release(prepared)

        return {
            "identifier_target_code": (
                object_metadata["identifier_target_code"]
            ),
            "generated_identifier": resolution.identifier,
        }
    #######################################################
    # Execute
    #################################################################

    #def execute(self, object_code: str):
    def execute(self, object_code: str, input_data: dict | None = None):

        if input_data is None:
            input_data = {}

        self.logger.header()
        self.repository_generator = RepositoryGenerator()

        #############################################################
        # STEP-001 Load Object Metadata
        #############################################################
        try:

            object_metadata = self._load_object_metadata(object_code)

        except Exception as ex:

            self.logger.step(1, "Load Object Metadata", "FAILED")
            self.logger.info("Message", str(ex))
            self.logger.footer()

            return {
                "success": False,
                "message": str(ex)
            }        

        self.logger.step(1, "Load Object Metadata")

        self.logger.info("Object ID", object_metadata["object_id"])
        self.logger.info("Object Code", object_metadata["object_code"])
        self.logger.info("Object Name", object_metadata["object_name"])
        self.logger.info(
            "Identifier Target",
            object_metadata["identifier_target_code"]
        )

        #############################################################
        # STEP-002 Build Execution Plan
        #############################################################
        execution_plan = self._build_execution_plan(object_metadata)

        self.logger.step(2, "Build Execution Plan")

        for plan in execution_plan:

            self.logger.info(
                f"STEP-{plan['step_no']:03d}",
                plan["step_name"]
            )

        #############################################################
        # STEP-003 Pre-Identity Intelligence
        #############################################################

        pre_identity_decision = self.pre_identity_intelligence.decide(
            object_code,
            {}
        )

        self.logger.step(3, "Pre-Identity Intelligence")

        self.logger.info(
            "Intelligence Type",
            pre_identity_decision["intelligence_type"]
        )

        self.logger.info(
            "Book Policy",
            pre_identity_decision["book_policy"]
        )

        self.logger.info(
            "Book ID Policy",
            pre_identity_decision["book_id_policy"]
        )

        self.logger.info(
            "Version Policy",
            pre_identity_decision["book_version_policy"]
        )

        self.logger.info(
            "Read Session Policy",
            pre_identity_decision["read_session_policy"]
        )

        self.logger.info(
            "Knowledge Unit",
            pre_identity_decision["knowledge_unit_policy"]
        )

        self.logger.info(
            "Status",
            pre_identity_decision["status"]
        )
        #############################################################
        # STEP-004 Generate Identifier
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
        # STEP-005 Build Repository Save Request
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
        # STEP-006 Repository Generator Save
        #############################################################

        repository_generator_result = self.repository_generator.save(
            repository_save_request
        )

        self.logger.step(6, "Repository Generator Save")

        repository_save_result = repository_generator_result

        self.logger.info(
            "Generator",
            repository_generator_result["generator"]
        )

        self.logger.info(
            "Status",
            repository_generator_result["status"]
        )

        #############################################################
        # STEP-007 Build MongoDB Save Request
        #############################################################

        # mongodb_save_request = self._build_mongodb_save_request(
        #     object_metadata,
        #     identifier_result,
        #     repository_generator_result
        # )
        mongodb_save_request = {
            "mongodb_document_id": identifier_result["generated_identifier"],
            "object_code": object_metadata["object_code"],
            "target_collection": object_metadata["object_id"],
            "repository_status_code": repository_generator_result["status"],
            "save_status": "READY",
        }

        self.logger.step(7, "Build MongoDB Save Request")

        self.logger.info(
            "MongoDB Document ID",
            mongodb_save_request["mongodb_document_id"]
        )

        self.logger.info(
            "Object Code",
            mongodb_save_request["object_code"]
        )

        self.logger.info(
            "Target Collection",
            mongodb_save_request["target_collection"]
        )

        self.logger.info(
            "Save Status",
            mongodb_save_request["save_status"]
        )

        #############################################################
        # STEP-008 Repository Intelligence
        #############################################################

        repository_intelligence_result = self._run_repository_intelligence(
            object_metadata,
            mongodb_save_request
        )

        self.logger.step(8, "Repository Intelligence")

        self.logger.info(
            "Intelligence Type",
            repository_intelligence_result["intelligence_type"]
        )

        self.logger.info(
            "Object Code",
            repository_intelligence_result["object_code"]
        )

        self.logger.info(
            "Repository Thinking",
            repository_intelligence_result["repository_thinking_yn"]
        )

        self.logger.info(
            "AI Ready",
            repository_intelligence_result["ai_ready_yn"]
        )

        self.logger.info(
            "Status",
            repository_intelligence_result["status"]
        )

        #############################################################
        # STEP-009 Build Execution History Request
        #############################################################

        execution_history_request = self._build_execution_history_request(
            object_code,
            object_metadata,
            identifier_result,
            repository_generator_result,
            mongodb_save_request
        )
        execution_history_metadata = self.execution_history_generator.load_identity_metadata(self.database)
        execution_history_identifier_result = self._generate_identifier(execution_history_metadata)
        execution_history_request["execution_history_id"] = execution_history_identifier_result["generated_identifier"]

        self.logger.step(9, "Build Execution History Request")

        self.logger.info(
            "Trace ID",
            execution_history_request["trace_id"]
        )

        self.logger.info(
            "Engine Code",
            execution_history_request["engine_code"]
        )

        self.logger.info(
            "Object Code",
            execution_history_request["object_code"]
        )

        self.logger.info(
            "Execution Status",
            execution_history_request["execution_status_code"]
        )

        self.logger.info(
            "History Status",
            execution_history_request["history_status_code"]
        )

        #############################################################
        # STEP-010 Execution History Generator Save
        #############################################################

        # execution_history_generator_result = self.execution_history_generator.save(
        #     execution_history_request
        # )
        execution_history_generator_result = self.execution_history_generator.save(
            execution_history_request,
            self.database
        )

        self.logger.step(10, "Execution History Generator Save")

        self.logger.info(
            "Generator",
            execution_history_generator_result["generator"]
        )

        self.logger.info(
            "Execution History ID",
            execution_history_generator_result["execution_history_id"]
        )

        self.logger.info(
            "Status",
            execution_history_generator_result["status"]
        )
        #############################################################
        # STEP-011 Build MongoDB Collection Request
        #############################################################

        mongodb_collection_request = self._build_mongodb_collection_request(
            object_metadata
        )

        self.logger.step(11, "Build MongoDB Collection Request")
        self.logger.info(
            "Object Code",
            mongodb_collection_request["object_code"]
        )
        self.logger.info(
            "Collection Name",
            mongodb_collection_request["collection_name"]
        )
        self.logger.info(
            "Request Status",
            mongodb_collection_request["request_status"]
        )

        #############################################################
        # STEP-012 Save MongoDB Collection
        #############################################################

        mongodb_collection_generator_result = \
            self.mongodb_collection_generator.save(
                mongodb_collection_request
            )

        self.logger.step(12, "MongoDB Collection Generator Save")
        self.logger.info(
            "Generator",
            mongodb_collection_generator_result["generator"]
        )
        self.logger.info(
            "Database Name",
            mongodb_collection_generator_result["database_name"]
        )
        self.logger.info(
            "Collection Name",
            mongodb_collection_generator_result["collection_name"]
        )
        self.logger.info(
            "Created",
            mongodb_collection_generator_result["created_yn"]
        )
        self.logger.info(
            "Status",
            mongodb_collection_generator_result["status"]
        )
        knowledge_document_result = self.knowledge_document_generator.generate(
            object_metadata=object_metadata,
            identifier_result=identifier_result,
            input_data=input_data,
        )
        input_data["knowledge_document"] = knowledge_document_result
        mongodb_document_request = self._build_mongodb_document_request(
            object_metadata,
            identifier_result,
            repository_generator_result,
            input_data,
        )
        #############################################################
        # STEP-013 Save MongoDB document
        #############################################################
        mongodb_document_result = (
            self.mongodb_document_generator.save(
                mongodb_document_request
            )
        )

        self.logger.step(
            13,
            "MongoDB Document Generator Save",
        )

        self.logger.info(
            "Generator",
            mongodb_document_result["generator"],
        )

        self.logger.info(
            "Inserted ID",
            mongodb_document_result.get(
                "inserted_id"
            ),
        )

        self.logger.info(
            "Status",
            mongodb_document_result["status"],
        )
        #############################################################
        # Generate Knowledge Document
        #############################################################

        knowledge_document_result = (
            self.knowledge_document_generator.generate(
                object_metadata=object_metadata,
                identifier_result=identifier_result,
                input_data=input_data,
            )
        )

        input_data["knowledge_document"] = (
            knowledge_document_result
        )

        self.logger.step(
            5,
            "Knowledge Document Generator",
        )

        self.logger.info(
            "Knowledge Document ID",
            knowledge_document_result[
                "knowledge_document_id"
            ],
        )

        self.logger.info(
            "Text Length",
            knowledge_document_result[
                "analysis"
            ]["text_length"],
        )        
        #############################################################
        return {
            "status": "READY",
            "object_code": object_code,
            "input_data": input_data,
            "object_metadata": object_metadata,
            "execution_plan": execution_plan,
            "pre_identity_decision": pre_identity_decision,
            "identifier_result": identifier_result,
            "repository_save_request": repository_save_request,
            "mongodb_save_request": mongodb_save_request,
            "knowledge_document_result": knowledge_document_result,
            "mongodb_document_request": mongodb_document_request,
            "mongodb_document_result": mongodb_document_result,
            "repository_intelligence_result": repository_intelligence_result,
            "execution_history_request": execution_history_request,
            "execution_history_generator_result": execution_history_generator_result,
            "mongodb_collection_request": mongodb_collection_request,
            "mongodb_collection_generator_result": mongodb_collection_generator_result
        }

    #################################################################
    # Load Object Metadata
    #################################################################

    def _load_object_metadata(self, object_code: str):
        sql = """
            SELECT
                object_id,
                object_code,
                object_name,
                business_code,
                domain_code,
                object_type_code,
                object_level,
                sequence_scope_code,
                sequence_length,
                identifier_target_code
            FROM sp_object
            WHERE object_code = %s
            AND active_yn = 'Y'
            AND status_code = 'ACTIVE'
            LIMIT 1
        """

        rows = self.database.fetch_all(sql, (object_code,))

        if not rows:
            raise RuntimeError(f"Object metadata not found. object_code={object_code}")

        return rows[0]
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
                "step_code": "BUILD_EXECUTION_PLAN",
                "step_name": "Build Execution Plan"
            },
            {
                "step_no": 3,
                "step_code": "PRE_IDENTITY_INTELLIGENCE",
                "step_name": "Pre-Identity Intelligence"
            },
            {
                "step_no": 4,
                "step_code": "GENERATE_IDENTIFIER",
                "step_name": "Generate Identifier"
            },
            {
                "step_no": 5,
                "step_code": "BUILD_REPOSITORY_SAVE_REQUEST",
                "step_name": "Build Repository Save Request"
            },
            {
                "step_no": 6,
                "step_code": "REPOSITORY_GENERATOR_SAVE",
                "step_name": "Repository Generator Save"
            },
            {
                "step_no": 7,
                "step_code": "BUILD_MONGODB_SAVE_REQUEST",
                "step_name": "Build MongoDB Save Request"
            },
            {
                "step_no": 8,
                "step_code": "REPOSITORY_INTELLIGENCE",
                "step_name": "Repository Intelligence"
            },
            {
                "step_no": 9,
                "step_code": "BUILD_EXECUTION_HISTORY_REQUEST",
                "step_name": "Build Execution History Request"
            },
            {
                "step_no": 10,
                "step_code": "EXECUTION_HISTORY_GENERATOR_SAVE",
                "step_name": "Execution History Generator Save"
            },
            {
                "step_no": 11,
                "step_code": "MONGODB_COLLECTION_GENERATOR_SAVE",
                "step_name": "Build MongoDB Collection Request"
            },
            {
                "step_no": 12,
                "step_code": "SAVE_MONGODB_COLLECTION",
                "step_name": "Save MongoDB Collection"
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

    #################################################################
    # Build MongoDB Save Request
    #################################################################

    def _build_mongodb_document_request(
        self,
        object_metadata,
        identifier_result,
        repository_generator_result,
        input_data,
    ):
        knowledge_document = input_data.get(
            "knowledge_document"
        )

        if not knowledge_document:
            raise RuntimeError(
                "Knowledge Document generation failed."
            )

        return {
            "mongodb_document_id": (
                identifier_result["generated_identifier"]
            ),
            "object_id": object_metadata["object_id"],
            "object_code": object_metadata["object_code"],
            "collection_name": object_metadata["object_id"],
            "repository_status_code": (
                repository_generator_result["status"]
            ),
            "knowledge_document": knowledge_document,
            "status": "READY",
        }

    def _read_object_comment_metadata(self, object_metadata):

        comment_metadata = {

            "object_role": "Semantic Document Object",

            "identifier_target": "DC",

            "generator": "RepositoryGenerator",

            "storage": [
                "Repository",
                "MongoDB"
            ],

            "alias": [
                "문서",
                "문건",
                "도큐먼트"
            ],

            "keywords": [
                "계약서",
                "보고서",
                "신청서"
            ],

            "engine_hint":
                "Generate Identifier -> Repository -> MongoDB",

            "generator_hint":
                "Repository Save then MongoDB Save"

        }

        return comment_metadata
    
    #################################################################
    # Build Execution History Request
    #################################################################

    def _build_execution_history_request(
        self,
        object_code,
        object_metadata,
        identifier_result,
        repository_generator_result,
        mongodb_save_request
    ):
        trace_id = datetime.now().strftime("TR_%Y%m%d_%H%M%S")

        return {
            "trace_id": trace_id,
            "engine_code": "OBJECT_RUNTIME",
            "object_code": object_code,
            "object_id": object_metadata["object_id"],
            "generated_identifier": identifier_result["generated_identifier"],
            "repository_status_code": repository_generator_result["status"],
            "mongodb_status_code": mongodb_save_request["save_status"],
            "execution_status_code": "SUCCESS",
            "history_status_code": "READY"
        }
    
    #################################################################
    # Repository Intelligence
    #################################################################

    def _run_repository_intelligence(
        self,
        object_metadata,
        mongodb_save_request
    ):
        return {
            "intelligence_type": "REPOSITORY_INTELLIGENCE",
            "object_code": object_metadata["object_code"],
            "object_role": "Semantic Object",
            "repository_thinking_yn": "Y",
            "ai_ready_yn": "Y" if self.ai_engine.is_ready() else "N",
            "interpretation": (
                "Repository preserves object knowledge. "
                "Engine interprets repository knowledge."
            ),
            "status": "SUCCESS"
        }
    #################################################################
    # 메서드 추가
    #################################################################
    def _build_mongodb_collection_request(self, object_metadata):
        return {
            "object_id": object_metadata["object_id"],
            "object_code": object_metadata["object_code"],
            "collection_name": object_metadata["object_id"],
            "create_if_not_exists": True,
            "request_status": "READY"
        }
    #################################################################
    # DOCUMENT Object를 만들기 위해
    # 무슨 순서로 실행할지 계획표를 만든다.
    #################################################################
    def _build_execution_plan(self, object_metadata: dict) -> list:
        """
        Object Metadata를 기준으로 Execution Plan을 생성한다.

        현재는 Prototype이므로 고정 Plan을 사용한다.
        다음 단계에서 Repository Rule 기반 Plan으로 교체한다.
        """

        return [
            {
                "step_no": 1,
                "step_code": "LOAD_OBJECT_METADATA",
                "step_name": "Load Object Metadata",
                "status": "READY"
            },
            {
                "step_no": 2,
                "step_code": "GENERATE_IDENTIFIER",
                "step_name": "Generate Identifier",
                "status": "READY",
                "identifier_target_code": object_metadata.get("identifier_target_code")
            },
            {
                "step_no": 3,
                "step_code": "SAVE_REPOSITORY",
                "step_name": "Save Repository",
                "status": "READY"
            },
            {
                "step_no": 4,
                "step_code": "SAVE_MONGODB",
                "step_name": "Save MongoDB",
                "status": "READY"
            },
            {
                "step_no": 5,
                "step_code": "SAVE_EXECUTION_LINK",
                "step_name": "Save Execution Link",
                "status": "READY"
            }
        ]
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
