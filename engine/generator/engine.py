from __future__ import annotations

from engine.generator.executor import GeneratorExecutor
from engine.generator.model import (
    GeneratorExecutionResult,
    GeneratorRequest,
)
from engine.generator.planner import GeneratorPlanner
from engine.generator.ports import RepositoryDefinitionResolver


class UnifiedGeneratorEngine:
    """
    SPS 통합 Generator 진입점.

    외부에서는 execute(request) 하나만 호출한다.
    """

    def __init__(
        self,
        resolver: RepositoryDefinitionResolver,
        planner: GeneratorPlanner,
        executor: GeneratorExecutor,
    ) -> None:
        self._resolver = resolver
        self._planner = planner
        self._executor = executor

    def execute(
        self,
        request: GeneratorRequest,
    ) -> GeneratorExecutionResult:
        definition = self._resolver.resolve(request.object_id)

        plan = self._planner.build(
            request=request,
            definition=definition,
        )

        artifacts = self._executor.execute(
            definition=definition,
            plan=plan,
        )

        return GeneratorExecutionResult(
            object_id=definition.object_id,
            object_code=definition.object_code,
            plan=plan,
            artifacts=artifacts,
        )
