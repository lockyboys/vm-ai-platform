from __future__ import annotations

from engine.generator.model import (
    ArtifactResult,
    GeneratorPlanStep,
    ObjectDefinition,
    PlanStepStatus,
)


class NoOpArtifactGenerator:
    """
    통합 구조 검증용 임시 Artifact Generator.

    실제 파일을 생성하지 않고 실행 흐름만 검증한다.
    이후 TableGenerator, EntityGenerator 등으로 교체한다.
    """

    def generate(
        self,
        definition: ObjectDefinition,
        step: GeneratorPlanStep,
    ) -> ArtifactResult:
        return ArtifactResult(
            artifact_type=step.artifact_type,
            status=PlanStepStatus.COMPLETED,
            output_path=None,
            message=(
                f"{step.artifact_type.value} generation simulation "
                f"completed for {definition.object_code}."
            ),
        )
