"""
========================================================================
SPS Base Engine
========================================================================

Responsibility
--------------------------------------------------------------------------
- 모든 Engine의 공통 Life Cycle 제공
- ExecutionContext 기반 실행
- Generator 호출 순서 제어
- Transaction 소유
- Cleanup 보장
- 기존 dict 요청 하위 호환

Rules
--------------------------------------------------------------------------
- Engine이 판단하고 통제한다.
- Generator는 생성만 수행한다.
- Cleanup은 성공과 실패에 관계없이 반드시 실행한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any

from engine.core.execution_context import ExecutionContext
from engine.core.execution_plan import ExecutionPlan
from engine.core.execution_result import ExecutionResult


class BaseEngine(ABC):
    """SPS Engine 공통 실행 생명주기."""

    def execute(
        self,
        request_or_context: dict[str, Any] | ExecutionContext,
    ) -> Any:
        """
        Engine 공통 실행 진입점.

        하위 호환:
            engine.execute({...})

        표준 호출:
            engine.execute(ExecutionContext(request={...}))
        """
        context = self._ensure_context(request_or_context)

        try:
            context.request = self.normalize_request(
                context.request
            )

            self.validate_request(context.request)

            context.execution_plan = self.build_execution_plan(
                context.request
            )

            self.pre_execute(context)

            with self.transaction():
                context.repository = self.resolve_repository(
                    context
                )

                context.identifier = self.resolve_identifier(
                    context
                )

                context.result = self.execute_generator(
                    context=context,
                )

                self.verify_result(
                    context.result,
                    context,
                )

            self.post_execute(context)

            self.record_execution_history(context)

            return context.result

        except Exception as exc:
            context.result = self.build_failure_result(
                context=context,
                exception=exc,
            )

            self.on_error(
                context=context,
                exception=exc,
            )

            raise

        finally:
            self.cleanup(context)

    def _ensure_context(
        self,
        request_or_context: dict[str, Any] | ExecutionContext,
    ) -> ExecutionContext:
        if isinstance(request_or_context, ExecutionContext):
            return request_or_context

        if isinstance(request_or_context, dict):
            return ExecutionContext(
                request=dict(request_or_context)
            )

        raise TypeError(
            "execute() requires dict or ExecutionContext. "
            f"received={type(request_or_context).__name__}"
        )

    def normalize_request(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        return request

    def validate_request(
        self,
        request: dict[str, Any],
    ) -> None:
        return None

    def build_execution_plan(
        self,
        request: dict[str, Any],
    ) -> ExecutionPlan | Any:
        return ExecutionPlan(
            name=self.__class__.__name__,
            steps=[],
        )

    def pre_execute(
        self,
        context: ExecutionContext,
    ) -> None:
        return None

    def post_execute(
        self,
        context: ExecutionContext,
    ) -> None:
        return None

    def verify_result(
        self,
        result: Any,
        context: ExecutionContext,
    ) -> None:
        return None

    def record_execution_history(
        self,
        context: ExecutionContext,
    ) -> None:
        return None

    def resolve_repository(
        self,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        return {}

    def resolve_identifier(
        self,
        context: ExecutionContext,
    ) -> str | None:
        return None

    def build_failure_result(
        self,
        *,
        context: ExecutionContext,
        exception: Exception,
    ) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            identifier=context.identifier,
            message=str(exception),
        )

    def on_error(
        self,
        *,
        context: ExecutionContext,
        exception: Exception,
    ) -> None:
        return None

    def cleanup(
        self,
        context: ExecutionContext,
    ) -> None:
        """
        성공·실패 여부와 관계없이 반드시 실행되는 정리 Hook.

        사용 예:
        - Named Lock 해제
        - 임시 파일 제거
        - 임시 Context 제거
        - Cache 정리
        """
        return None

    @contextmanager
    def transaction(self):
        self.begin_transaction()

        try:
            yield
            self.commit_transaction()

        except Exception:
            self.rollback_transaction()
            raise

    def begin_transaction(self) -> None:
        return None

    def commit_transaction(self) -> None:
        return None

    def rollback_transaction(self) -> None:
        return None

    @abstractmethod
    def execute_generator(
        self,
        *,
        context: ExecutionContext,
    ) -> Any:
        """Engine별 Generator 호출."""
        raise NotImplementedError
