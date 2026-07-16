from __future__ import annotations

from collections.abc import Mapping

from engine.generator.model import (
    ArtifactResult,
    ArtifactType,
    GeneratorExecutionPlan,
    GeneratorPlanStep,
    ObjectDefinition,
    PlanStepStatus,
)
from engine.generator.ports import ArtifactGenerator


class GeneratorExecutor:
    """
    Execution Plan에 포함된 READY Step만 실행한다.
    """

    def __init__(
        self,
        generators: Mapping[ArtifactType, ArtifactGenerator],
    ) -> None:
        self._generators = dict(generators)

    def execute(
        self,
        definition: ObjectDefinition,
        plan: GeneratorExecutionPlan,
    ) -> tuple[ArtifactResult, ...]:
        results: list[ArtifactResult] = []

        for step in plan.steps:
            if step.status == PlanStepStatus.SKIPPED:
                results.append(
                    ArtifactResult(
                        artifact_type=step.artifact_type,
                        status=PlanStepStatus.SKIPPED,
                        message=step.reason,
                    )
                )
                continue

            generator = self._generators.get(step.artifact_type)

            if generator is None:
                results.append(
                    ArtifactResult(
                        artifact_type=step.artifact_type,
                        status=PlanStepStatus.FAILED,
                        message=(
                            "Artifact Generator is not registered: "
                            f"{step.artifact_type.value}"
                        ),
                    )
                )
                continue

            try:
                result = generator.generate(
                    definition=definition,
                    step=step,
                )
            except Exception as exc:
                result = ArtifactResult(
                    artifact_type=step.artifact_type,
                    status=PlanStepStatus.FAILED,
                    message=str(exc),
                )

            results.append(result)

        return tuple(results)
