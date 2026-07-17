from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path("/data/vm_project")

SEARCH_EXTENSIONS = {
    ".py": "PYTHON",
    ".sql": "SQL",
    ".md": "MARKDOWN",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
}

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".home",
}

DEFAULT_MAX_RESULTS = 100
MAX_ALLOWED_RESULTS = 500


def source_search(
    keyword: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    case_sensitive: bool = False,
) -> list[dict]:
    """Search project text files and return matching lines."""

    normalized_keyword = keyword.strip()

    if not normalized_keyword:
        raise ValueError("keyword must not be empty.")

    normalized_max_results = max(
        1,
        min(max_results, MAX_ALLOWED_RESULTS),
    )

    search_keyword = (
        normalized_keyword
        if case_sensitive
        else normalized_keyword.lower()
    )

    results: list[dict] = []

    for path in sorted(PROJECT_ROOT.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(PROJECT_ROOT)

        if any(
            directory_name in EXCLUDED_DIRECTORY_NAMES
            for directory_name in relative_path.parts
        ):
            continue

        file_type = SEARCH_EXTENSIONS.get(path.suffix.lower())

        if file_type is None:
            continue

        try:
            with path.open(
                mode="r",
                encoding="utf-8",
                errors="ignore",
            ) as source_file:
                for line_no, line_text in enumerate(
                    source_file,
                    start=1,
                ):
                    comparison_text = (
                        line_text
                        if case_sensitive
                        else line_text.lower()
                    )

                    if search_keyword not in comparison_text:
                        continue

                    results.append(
                        {
                            "path": str(relative_path),
                            "line_no": line_no,
                            "line_text": line_text.rstrip(),
                            "file_type": file_type,
                        }
                    )

                    if len(results) >= normalized_max_results:
                        return results

        except OSError:
            continue

    return results

DEFAULT_START_LINE = 1
DEFAULT_MAX_LINES = 200
MAX_ALLOWED_LINES = 1000


def source_read(
    path: str,
    start_line: int = DEFAULT_START_LINE,
    max_lines: int = DEFAULT_MAX_LINES,
) -> dict:
    """Read a project text file with line numbers."""

    normalized_path = path.strip()

    if not normalized_path:
        raise ValueError("path must not be empty.")

    requested_path = (PROJECT_ROOT / normalized_path).resolve()
    project_root = PROJECT_ROOT.resolve()

    if requested_path != project_root and project_root not in requested_path.parents:
        raise ValueError("The requested path is outside the project root.")

    if not requested_path.exists():
        raise FileNotFoundError(
            f"Source file was not found: {normalized_path}"
        )

    if not requested_path.is_file():
        raise ValueError(
            f"The requested path is not a file: {normalized_path}"
        )

    normalized_start_line = max(1, start_line)
    normalized_max_lines = max(
        1,
        min(max_lines, MAX_ALLOWED_LINES),
    )

    lines = requested_path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()

    start_index = normalized_start_line - 1
    end_index = min(
        start_index + normalized_max_lines,
        len(lines),
    )

    content = [
        {
            "line_no": line_no,
            "line_text": lines[line_no - 1],
        }
        for line_no in range(
            normalized_start_line,
            end_index + 1,
        )
    ]

    return {
        "path": str(requested_path.relative_to(project_root)),
        "start_line": normalized_start_line,
        "end_line": end_index,
        "total_lines": len(lines),
        "content": content,
    }