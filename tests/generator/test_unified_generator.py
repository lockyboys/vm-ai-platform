from __future__ import annotations

from engine.generator.artifact.noop_generator import (
    NoOpArtifactGenerator,
)
from engine.generator.engine import UnifiedGeneratorEngine
from engine.generator.executor import GeneratorExecutor
from engine.generator.model import (
    ArtifactType,
    AttributeDefinition,
    GeneratorRequest,
    MetadataConstraint,
    ObjectDefinition,
    PlanStepStatus,
    RelationshipDefinition,
)
from engine.generator.planner import GeneratorPlanner


class InMemoryRepositoryDefinitionResolver:
    """
    테스트 전용 Resolver.

    실제 운영 구현에서는 Repository DB 조회 Adapter로 교체한다.
    """

    def resolve(self, object_id: str) -> ObjectDefinition:
        if object_id != "OB_TEST_CM_ROLE_RULE":
            raise LookupError(
                f"Repository Object not found: {object_id}"
            )

        role_id_metadata = MetadataConstraint(
            metadata_code="ROLE_ID_LENGTH",
            constraint_type_code="MAX_LENGTH",
            constraint_value=30,
            target_attribute_code="role_id",
            description="role_id 최대 길이 제한",
        )

        rule_id_metadata = MetadataConstraint(
            metadata_code="RULE_ID_LENGTH",
            constraint_type_code="MAX_LENGTH",
            constraint_value=30,
            target_attribute_code="rule_id",
            description="rule_id 최대 길이 제한",
        )

        return ObjectDefinition(
            object_id="OB_TEST_CM_ROLE_RULE",
            object_code="CM_ROLE_RULE",
            object_name="Role Rule Mapping",
            object_type_code="MAPPING",
            attributes=(
                AttributeDefinition(
                    attribute_id="AT_TEST_ROLE_ID",
                    attribute_code="role_id",
                    attribute_name="Role ID",
                    data_type_code="VARCHAR",
                    nullable=False,
                    ordinal_no=1,
                    length=30,
                    metadata_constraints=(role_id_metadata,),
                ),
                AttributeDefinition(
                    attribute_id="AT_TEST_RULE_ID",
                    attribute_code="rule_id",
                    attribute_name="Rule ID",
                    data_type_code="VARCHAR",
                    nullable=False,
                    ordinal_no=2,
                    length=30,
                    metadata_constraints=(rule_id_metadata,),
                ),
            ),
            relationships=(
                RelationshipDefinition(
                    relationship_id="RE_TEST_ROLE",
                    relationship_code="CM_ROLE_RULE_TO_CM_ROLE",
                    source_object_id="OB_TEST_CM_ROLE_RULE",
                    target_object_id="OB_TEST_CM_ROLE",
                    relationship_type_code="MANY_TO_ONE",
                    source_attribute_code="role_id",
                    target_attribute_code="role_id",
                ),
                RelationshipDefinition(
                    relationship_id="RE_TEST_RULE",
                    relationship_code="CM_ROLE_RULE_TO_RL_RULE",
                    source_object_id="OB_TEST_CM_ROLE_RULE",
                    target_object_id="OB_TEST_RL_RULE",
                    relationship_type_code="MANY_TO_ONE",
                    source_attribute_code="rule_id",
                    target_attribute_code="rule_id",
                ),
            ),
        )


def test_unified_generator_execution() -> None:
    resolver = InMemoryRepositoryDefinitionResolver()
    planner = GeneratorPlanner()

    noop = NoOpArtifactGenerator()

    executor = GeneratorExecutor(
        generators={
            ArtifactType.TABLE: noop,
            ArtifactType.ENTITY: noop,
            ArtifactType.REPOSITORY: noop,
        }
    )

    engine = UnifiedGeneratorEngine(
        resolver=resolver,
        planner=planner,
        executor=executor,
    )

    request = GeneratorRequest(
        object_id="OB_TEST_CM_ROLE_RULE",
        requested_artifacts=(
            ArtifactType.TABLE,
            ArtifactType.ENTITY,
            ArtifactType.REPOSITORY,
        ),
    )

    result = engine.execute(request)

    assert result.object_code == "CM_ROLE_RULE"
    assert result.succeeded is True

    completed = [
        item
        for item in result.artifacts
        if item.status == PlanStepStatus.COMPLETED
    ]

    skipped = [
        item
        for item in result.artifacts
        if item.status == PlanStepStatus.SKIPPED
    ]

    assert len(completed) == 3
    assert len(skipped) == 7


def test_metadata_is_constraint_not_object_definition() -> None:
    resolver = InMemoryRepositoryDefinitionResolver()
    definition = resolver.resolve("OB_TEST_CM_ROLE_RULE")

    role_id = definition.attributes[0]
    metadata = role_id.metadata_constraints[0]

    assert metadata.constraint_type_code == "MAX_LENGTH"
    assert metadata.constraint_value == 30
    assert metadata.target_attribute_code == "role_id"
