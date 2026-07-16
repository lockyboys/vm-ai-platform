from __future__ import annotations

from typing import Protocol

from engine.generator.model import (
    ArtifactResult,
    GeneratorPlanStep,
    ObjectDefinition,
)


class RepositoryDefinitionResolver(Protocol):
    """
    Repository Object 정의 조회 포트.

    구현체는 실제 Repository에서 Object, Attribute, Relationship,
    Metadata Constraint를 조회하여 ObjectDefinition으로 반환한다.
    """

    def resolve(self, object_id: str) -> ObjectDefinition:
        ...


class ArtifactGenerator(Protocol):
    """
    개별 Artifact Generator 포트.

    Table, Entity, DTO 등 개별 생성기는 동일한 인터페이스를 사용한다.
    """

    def generate(
        self,
        definition: ObjectDefinition,
        step: GeneratorPlanStep,
    ) -> ArtifactResult:
        ...
