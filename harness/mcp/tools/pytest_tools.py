from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import pytest

from harness.mcp.formatters.pytest_result_formatter import (
    PytestCaseResult,
    PytestResultFormatter,
)


@dataclass
class PytestResultCollector:
    """pytest Hook 기반 테스트 결과 수집기."""

    results: list[PytestCaseResult] = field(
        default_factory=list
    )

    def pytest_runtest_logreport(
        self,
        report: Any,
    ) -> None:
        """
        pytest 실행 단계별 Report를 수집한다.

        정상 테스트는 call 단계에서 수집한다.
        setup/teardown 오류는 ERROR로 수집한다.
        """

        if report.when == "call":
            self.results.append(
                PytestCaseResult(
                    node_id=report.nodeid,
                    status=self._resolve_call_status(
                        report
                    ),
                    duration=float(
                        report.duration
                    ),
                    detail=self._resolve_detail(
                        report
                    ),
                )
            )

            return

        if (
            report.when in {
                "setup",
                "teardown",
            }
            and report.failed
        ):
            self.results.append(
                PytestCaseResult(
                    node_id=report.nodeid,
                    status="ERROR",
                    duration=float(
                        report.duration
                    ),
                    detail=self._resolve_detail(
                        report
                    ),
                )
            )

    @staticmethod
    def _resolve_call_status(
        report: Any,
    ) -> str:
        if report.passed:
            if hasattr(
                report,
                "wasxfail",
            ):
                return "XPASSED"

            return "PASSED"

        if report.skipped:
            if hasattr(
                report,
                "wasxfail",
            ):
                return "XFAILED"

            return "SKIPPED"

        return "FAILED"

    @staticmethod
    def _resolve_detail(
        report: Any,
    ) -> str:
        if not report.failed:
            return ""

        longreprtext = getattr(
            report,
            "longreprtext",
            "",
        )

        if longreprtext:
            return str(longreprtext)

        return str(
            getattr(
                report,
                "longrepr",
                "",
            )
        )


def run_pytest_verification(
    test_paths: Sequence[str],
    *,
    title: str = "Formatter Test Verification",
) -> dict[str, Any]:
    """
    pytest를 실행하고 SPS 구조화 출력물을 반환한다.

    pytest 기본 Terminal 출력은 내부에서 수집하고,
    최종 PrettyOutput만 Console에 표시한다.
    """

    if not test_paths:
        raise ValueError(
            "test_paths must not be empty."
        )

    missing_paths = [
        path
        for path in test_paths
        if not Path(path).exists()
    ]

    if missing_paths:
        raise FileNotFoundError(
            "Test path does not exist: "
            + ", ".join(missing_paths)
        )

    collector = PytestResultCollector()

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    pytest_arguments = [
        *test_paths,
        "--disable-warnings",
        "--tb=short",
        "-q",
    ]

    with (
        contextlib.redirect_stdout(
            stdout_buffer
        ),
        contextlib.redirect_stderr(
            stderr_buffer
        ),
    ):
        exit_code = pytest.main(
            pytest_arguments,
            plugins=[
                collector,
            ],
        )

    pretty_output = (
        PytestResultFormatter.format(
            collector.results,
            title=title,
        )
    )

    return {
        "exit_code": int(exit_code),
        "success": int(exit_code) == 0,
        "results": collector.results,
        "pretty_output": pretty_output,
        "raw_stdout": stdout_buffer.getvalue(),
        "raw_stderr": stderr_buffer.getvalue(),
    }
