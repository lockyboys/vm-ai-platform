from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class ArtifactType(str, Enum):
    """통합 Generator가 생성할 수 있는 산출물 유형."""

    TABLE = "TABLE"
    ENTITY = "ENTITY"
    DTO = "DTO"
    REPOSITORY = "REPOSITORY"
    SERVICE = "SERVICE"
    API = "API"
    CRUD_UI = "CRUD_UI"
    STATISTICS = "STATISTICS"
    DASHBOARD = "DASHBOARD"
    DOCUMENT = "DOCUMENT"


class PlanStepStatus(str, Enum):
    READY = "READY"
    SKIPPED = "SKIPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class MetadataConstraint:
    """
    SPS Metadata.

    Metadata는 Object/Attribute/Relationship 정의 자체가 아니다.
    용어, 길이, 형식, 마스크 및 검증 제한만 표현한다.
    """

    metadata_code: str
    constraint_type_code: str
    constraint_value: Any
    target_attribute_code: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class AttributeDefinition:
    attribute_id: str
    attribute_code: str
    attribute_name: str
    data_type_code: str
    nullable: bool
    ordinal_no: int

    length: int | None = None
    precision: int | None = None
    scale: int | None = None

    metadata_constraints: tuple[MetadataConstraint, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class RelationshipDefinition:
    relationship_id: str
    relationship_code: str
    source_object_id: str
    target_object_id: str
    relationship_type_code: str

    source_attribute_code: str | None = None
    target_attribute_code: str | None = None


@dataclass(frozen=True)
class ObjectDefinition:
    """
    Repository에 등록된 Object 정의.

    이 객체 자체를 Metadata라고 부르지 않는다.
    """

    object_id: str
    object_code: str
    object_name: str
    object_type_code: str

    attributes: tuple[AttributeDefinition, ...] = field(
        default_factory=tuple
    )
    relationships: tuple[RelationshipDefinition, ...] = field(
        default_factory=tuple
    )
    metadata_constraints: tuple[MetadataConstraint, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class GeneratorRequest:
    """
    통합 Generator 입력.

    object_id:
        Repository Object 식별자.

    requested_artifacts:
        이번 실행에서 생성할 산출물 목록.
        아직 별도 Generator Profile 테이블을 가정하지 않는다.

    options:
        실행 옵션. Repository 구조를 대체하지 않는다.
    """

    object_id: str
    requested_artifacts: tuple[ArtifactType, ...]
    options: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GeneratorPlanStep:
    step_no: int
    artifact_type: ArtifactType
    status: PlanStepStatus
    reason: str


@dataclass(frozen=True)
class GeneratorExecutionPlan:
    object_id: str
    object_code: str
    steps: tuple[GeneratorPlanStep, ...]

    @property
    def ready_steps(self) -> tuple[GeneratorPlanStep, ...]:
        return tuple(
            step
            for step in self.steps
            if step.status == PlanStepStatus.READY
        )


@dataclass(frozen=True)
class ArtifactResult:
    artifact_type: ArtifactType
    status: PlanStepStatus
    output_path: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class GeneratorExecutionResult:
    object_id: str
    object_code: str
    plan: GeneratorExecutionPlan
    artifacts: tuple[ArtifactResult, ...]

    @property
    def succeeded(self) -> bool:
        return all(
            artifact.status
            in {
                PlanStepStatus.COMPLETED,
                PlanStepStatus.SKIPPED,
            }
            for artifact in self.artifacts
        )
