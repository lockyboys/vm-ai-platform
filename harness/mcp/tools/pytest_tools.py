# =============================================================================
# File Name   : harness/mcp/tools/pytest_tools.py
# Purpose     : 테스트를 실행하고 결과를 보기 쉽게 알려 주는 도구
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260902 | Codex | Harness 표준 파일 헤더와 테스트 증적 역할을 보강했음
# =============================================================================
# 이 파일은 무엇을 하나요?
# - 사용자가 고른 테스트 파일만 실행하고, 성공·실패·오류를 나누어 알려 줍니다.
# - 긴 테스트 화면 대신 필요한 결과를 정리해 변경이 안전한지 확인하게 돕습니다.
# 주의: 테스트가 아닌 임의 명령어를 실행하지 않으며, 허용된 테스트 경로만 받습니다.
from __future__ import annotations

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from harness.mcp.formatters.pytest_result_formatter import (
    PytestCaseResult,
    PytestResultFormatter,
)

PROJECT_ROOT = Path("/data/vm_project")
MAX_TEST_PATHS = 20


@dataclass(eq=False)
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


def _validate_test_paths(test_paths: Sequence[str]) -> list[str]:
    if not test_paths:
        raise ValueError("test_paths must not be empty.")
    if len(test_paths) > MAX_TEST_PATHS:
        raise ValueError(f"No more than {MAX_TEST_PATHS} test paths are allowed.")

    project_root = PROJECT_ROOT.resolve(strict=True)
    normalized_paths: list[str] = []
    for path in test_paths:
        normalized_path = path.strip()
        relative_path = Path(normalized_path)
        if not normalized_path or relative_path.is_absolute():
            raise ValueError("Only non-empty project-relative test paths are allowed.")
        if any(part in {"", ".", ".."} for part in relative_path.parts):
            raise ValueError("Dot segments are not allowed in test paths.")
        if not relative_path.parts or relative_path.parts[0] != "tests":
            raise ValueError("Only tests/ paths are allowed.")

        requested_path = (project_root / relative_path).resolve(strict=True)
        if project_root not in requested_path.parents:
            raise ValueError("The requested test path is outside the project root.")

        canonical_path = str(requested_path.relative_to(project_root))
        if canonical_path not in normalized_paths:
            normalized_paths.append(canonical_path)
    return normalized_paths


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

    normalized_test_paths = _validate_test_paths(test_paths)

    # 20260831 | CODEX | MCP 이벤트 루프·모듈 캐시와 테스트 실행을 분리했음
    # 별도 Python 프로세스에서 pytest를 실행해야 asyncio.run() 테스트가
    # 정상 동작하고, 매 실행마다 수정된 소스를 새로 import할 수 있다.
    with tempfile.NamedTemporaryFile(
        prefix="sps_pytest_",
        suffix=".xml",
        delete=False,
    ) as junit_file:
        junit_path = Path(junit_file.name)

    pytest_arguments = [
        sys.executable,
        "-m",
        "pytest",
        *normalized_test_paths,
        "--disable-warnings",
        "--tb=short",
        "-q",
        f"--junitxml={junit_path}",
    ]
    try:
        completed = subprocess.run(
            pytest_arguments,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        results: list[PytestCaseResult] = []
        if junit_path.exists() and junit_path.stat().st_size:
            root = ElementTree.parse(junit_path).getroot()
            for test_case in root.iter("testcase"):
                file_path = test_case.get("file", "")
                case_name = test_case.get("name", "")
                class_name = test_case.get("classname", "")
                node_prefix = file_path or class_name.replace(".", "/") + ".py"
                node_id = f"{node_prefix}::{case_name}" if node_prefix else case_name
                status = "PASSED"
                detail = ""
                for child_name, child_status in (
                    ("failure", "FAILED"),
                    ("error", "ERROR"),
                    ("skipped", "SKIPPED"),
                ):
                    child = test_case.find(child_name)
                    if child is not None:
                        status = child_status
                        detail = child.text or child.get("message", "")
                        break
                results.append(
                    PytestCaseResult(
                        node_id=node_id,
                        status=status,
                        duration=float(test_case.get("time", "0") or 0),
                        detail=detail,
                    )
                )
    finally:
        junit_path.unlink(missing_ok=True)

    pretty_output = (
        PytestResultFormatter.format(
            results,
            title=title,
        )
    )

    return {
        "exit_code": int(completed.returncode),
        "success": completed.returncode == 0,
        "results": results,
        "pretty_output": pretty_output,
        "raw_stdout": completed.stdout,
        "raw_stderr": completed.stderr,
    }
