from __future__ import annotations

from engine.generator.model import (
    ArtifactType,
    GeneratorExecutionPlan,
    GeneratorPlanStep,
    GeneratorRequest,
    ObjectDefinition,
    PlanStepStatus,
)


class GeneratorPlanner:
    """
    Repository Object 정의와 Generator 요청을 바탕으로
    실행 계획만 생성한다.

    Planner는 파일을 생성하지 않는다.
    Planner는 Metadata를 생성하지 않는다.
    """

    _EXECUTION_ORDER: tuple[ArtifactType, ...] = (
        ArtifactType.TABLE,
        ArtifactType.ENTITY,
        ArtifactType.DTO,
        ArtifactType.REPOSITORY,
        ArtifactType.SERVICE,
        ArtifactType.API,
        ArtifactType.CRUD_UI,
        ArtifactType.STATISTICS,
        ArtifactType.DASHBOARD,
        ArtifactType.DOCUMENT,
    )

    def build(
        self,
        request: GeneratorRequest,
        definition: ObjectDefinition,
    ) -> GeneratorExecutionPlan:
        if request.object_id != definition.object_id:
            raise ValueError(
                "Generator request object_id and Repository "
                "definition object_id do not match."
            )

        requested = set(request.requested_artifacts)
        steps: list[GeneratorPlanStep] = []

        for artifact_type in self._EXECUTION_ORDER:
            if artifact_type in requested:
                status = PlanStepStatus.READY
                reason = "Requested by GeneratorRequest."
            else:
                status = PlanStepStatus.SKIPPED
                reason = "Not requested for this execution."

            steps.append(
                GeneratorPlanStep(
                    step_no=len(steps) + 1,
                    artifact_type=artifact_type,
                    status=status,
                    reason=reason,
                )
            )

        return GeneratorExecutionPlan(
            object_id=definition.object_id,
            object_code=definition.object_code,
            steps=tuple(steps),
        )
