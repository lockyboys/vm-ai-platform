from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.common.formatter import (
    PrettyOutput,
    TreeNode,
    TreeNodeType,
)


@dataclass(frozen=True)
class PytestCaseResult:
    """pytest 단위 테스트 실행 결과."""

    node_id: str
    status: str
    duration: float = 0.0
    detail: str = ""


class PytestResultFormatter:
    """pytest 결과를 SPS PrettyOutput 표준으로 변환한다."""

    STATUS_ICON_MAPPING: dict[str, str] = {
        "PASSED": "✅",
        "FAILED": "❌",
        "SKIPPED": "⏭️",
        "ERROR": "🚨",
        "XFAILED": "⚠️",
        "XPASSED": "⚠️",
    }

    @classmethod
    def format(
        cls,
        results: Iterable[PytestCaseResult],
        *,
        title: str = "Formatter Test Verification",
    ) -> str:
        normalized_results = tuple(results)

        status_count = cls._count_status(
            normalized_results
        )

        total_count = len(normalized_results)
        passed_count = status_count.get(
            "PASSED",
            0,
        )
        failed_count = status_count.get(
            "FAILED",
            0,
        )
        error_count = status_count.get(
            "ERROR",
            0,
        )
        skipped_count = status_count.get(
            "SKIPPED",
            0,
        )

        total_duration = sum(
            result.duration
            for result in normalized_results
        )

        verification_status = (
            "SUCCESS"
            if failed_count == 0
            and error_count == 0
            else "ERROR"
        )

        output = PrettyOutput(
            title,
            icon="🧪",
            status=verification_status,
        )

        output.summary(
            Total=total_count,
            Passed=passed_count,
            Failed=failed_count,
            Error=error_count,
            Skipped=skipped_count,
            Duration=f"{total_duration:.4f}s",
            Verification=verification_status,
        )

        output.logical_tree(
            title="Test Results",
            root=cls._build_result_tree(
                normalized_results
            ),
        )

        failure_lines = cls._build_failure_lines(
            normalized_results
        )

        if failure_lines:
            output.body(
                "Failure Details",
                *failure_lines,
            )

        return output.render()

    @classmethod
    def _build_tree_paths(
        cls,
        results: tuple[PytestCaseResult, ...],
    ) -> list[str]:
        paths: list[str] = []

        for result in results:
            normalized_node_id = (
                result.node_id
                .replace("\\", "/")
                .replace("::", "/")
            )

            if normalized_node_id.startswith(
                "tests/"
            ):
                normalized_node_id = (
                    normalized_node_id[
                        len("tests/"):
                    ]
                )

            status = result.status.upper()
            status_icon = (
                cls.STATUS_ICON_MAPPING.get(
                    status,
                    "•",
                )
            )

            paths.append(
                f"{normalized_node_id}/"
                f"{status_icon} {status}"
            )

        return paths

    @staticmethod
    def _count_status(
        results: tuple[PytestCaseResult, ...],
    ) -> dict[str, int]:
        status_count: dict[str, int] = {}

        for result in results:
            status = result.status.upper()

            status_count[status] = (
                status_count.get(
                    status,
                    0,
                )
                + 1
            )

        return status_count

    @staticmethod
    def _build_failure_lines(
        results: tuple[PytestCaseResult, ...],
    ) -> list[str]:
        lines: list[str] = []

        for result in results:
            if result.status.upper() not in {
                "FAILED",
                "ERROR",
                "XPASSED",
            }:
                continue

            lines.append(
                f"[{result.status.upper()}] "
                f"{result.node_id}"
            )

            if result.detail:
                lines.extend(
                    f"    {line}"
                    for line
                    in result.detail.splitlines()
                )

        return lines

    @classmethod
    def _build_result_tree(
        cls,
        results: tuple[PytestCaseResult, ...],
    ) -> TreeNode:
        root = TreeNode(
            name="tests",
            node_type=TreeNodeType.DIRECTORY,
        )

        for result in results:
            normalized_node_id = result.node_id.replace(
                "\\",
                "/",
            )

            file_path, separator, test_name = (
                normalized_node_id.partition("::")
            )

            path_parts = [
                part
                for part in file_path.split("/")
                if part
            ]

            if (
                path_parts
                and path_parts[0] == "tests"
            ):
                path_parts = path_parts[1:]

            current_node = root

            for index, part in enumerate(path_parts):
                is_test_file = (
                    index == len(path_parts) - 1
                )

                node_type = (
                    TreeNodeType.FILE
                    if is_test_file
                    else TreeNodeType.DIRECTORY
                )

                current_node = cls._get_or_create_child(
                    parent=current_node,
                    name=part,
                    node_type=node_type,
                )

            if separator and test_name:
                test_node = cls._get_or_create_child(
                    parent=current_node,
                    name=test_name,
                    node_type=TreeNodeType.LOGICAL,
                )

                status = result.status.upper()
                status_icon = (
                    cls.STATUS_ICON_MAPPING.get(
                        status,
                        "•",
                    )
                )

                cls._get_or_create_child(
                    parent=test_node,
                    name=f"{status_icon} {status}",
                    node_type=TreeNodeType.LOGICAL,
                )

        return root

    @staticmethod
    def _get_or_create_child(
        *,
        parent: TreeNode,
        name: str,
        node_type: TreeNodeType,
    ) -> TreeNode:
        for child in parent.children.values():
            if (
                child.name == name
                and child.node_type == node_type
            ):
                return child

        child = TreeNode(
            name=name,
            node_type=node_type,
        )

        parent.add_child(child)

        return child

# Public formatter API alias
format_pytest_result = PytestResultFormatter.format
