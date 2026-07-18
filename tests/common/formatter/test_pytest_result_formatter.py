from src.common.formatter import (
    TreeNode,
    TreeNodeType,
)

from harness.mcp.formatters.pytest_result_formatter import (
    PytestCaseResult,
    PytestResultFormatter,
)


def test_pytest_result_tree_output() -> None:
    results = [
        PytestCaseResult(
            node_id=(
                "tests/common/formatter/"
                "test_tree_formatter.py"
                "::test_render_directory_tree"
            ),
            status="PASSED",
            duration=0.01,
        ),
        PytestCaseResult(
            node_id=(
                "tests/common/formatter/"
                "test_tree_formatter.py"
                "::test_render_empty_paths"
            ),
            status="PASSED",
            duration=0.01,
        ),
    ]

    rendered = PytestResultFormatter.format(
        results
    )

    assert "Test Results" in rendered
    assert "common/" in rendered
    assert "formatter/" in rendered
    assert "test_tree_formatter.py" in rendered
    assert "test_render_directory_tree" in rendered
    assert "test_render_empty_paths" in rendered
    assert "PASSED" in rendered
    assert "Verification" in rendered
    assert "SUCCESS" in rendered


def test_pytest_failure_status_output() -> None:
    results = [
        PytestCaseResult(
            node_id=(
                "tests/common/formatter/"
                "test_sample.py"
                "::test_failure"
            ),
            status="FAILED",
            duration=0.01,
            detail="AssertionError: expected true",
        ),
    ]

    rendered = PytestResultFormatter.format(
        results
    )

    assert "FAILED" in rendered
    assert "ERROR" in rendered
    assert "AssertionError" in rendered


def test_pytest_file_is_not_rendered_as_directory() -> None:
    results = [
        PytestCaseResult(
            node_id=(
                "tests/common/formatter/"
                "test_pytest_result_formatter.py"
                "::test_pytest_result_tree_output"
            ),
            status="PASSED",
        ),
    ]

    rendered = PytestResultFormatter.format(
        results
    )

    assert (
        "test_pytest_result_formatter.py/"
        not in rendered
    )

    assert (
        "test_pytest_result_formatter.py"
        in rendered
    )

    assert (
        "test_pytest_result_tree_output/"
        not in rendered
    )

def test_logical_tree_node_has_no_directory_suffix() -> None:
    node = TreeNode(
        name="test_example",
        node_type=TreeNodeType.LOGICAL,
    )

    assert node.display_name == "test_example"


def test_file_tree_node_has_no_directory_suffix() -> None:
    node = TreeNode(
        name="test_example.py",
        node_type=TreeNodeType.FILE,
    )

    assert node.display_name == "test_example.py"


def test_directory_tree_node_has_directory_suffix() -> None:
    node = TreeNode(
        name="formatter",
        node_type=TreeNodeType.DIRECTORY,
    )

    assert node.display_name == "formatter/"
