from src.common.formatter.tree_formatter import (
    TreeFormatter,
)


def test_render_directory_tree() -> None:
    paths = [
        "src/common/formatter/pretty_output.py",
        "src/common/formatter/pretty_formatter.py",
        "tests/common/formatter/test_pretty_output.py",
    ]

    rendered = TreeFormatter.render(paths)

    expected = "\n".join(
        [
            ".",
            "├── src/",
            "│   └── common/",
            "│       └── formatter/",
            "│           ├── pretty_formatter.py",
            "│           └── pretty_output.py",
            "└── tests/",
            "    └── common/",
            "        └── formatter/",
            "            └── test_pretty_output.py",
        ]
    )

    assert rendered == expected


def test_render_removes_duplicate_paths() -> None:
    paths = [
        "src/common/file.py",
        "src/common/file.py",
        "./src/common/file.py",
    ]

    rendered = TreeFormatter.render(paths)

    assert rendered.count("file.py") == 1


def test_render_normalizes_windows_paths() -> None:
    paths = [
        r"src\common\formatter\pretty_output.py",
    ]

    rendered = TreeFormatter.render(paths)

    assert "src/" in rendered
    assert "common/" in rendered
    assert "formatter/" in rendered
    assert "pretty_output.py" in rendered


def test_render_empty_paths() -> None:
    rendered = TreeFormatter.render([])

    assert rendered == "."


def test_render_custom_root_name() -> None:
    rendered = TreeFormatter.render(
        [
            "harness/mcp/tools/git_tools.py",
        ],
        root_name="project/",
    )

    assert rendered.startswith("project/")
    assert "harness/" in rendered
    assert "git_tools.py" in rendered


def test_directories_are_rendered_before_files() -> None:
    paths = [
        "README.md",
        "src/common/file.py",
        ".gitignore",
    ]

    rendered = TreeFormatter.render(paths)
    lines = rendered.splitlines()

    src_index = lines.index("├── src/")
    gitignore_index = lines.index("├── .gitignore")
    readme_index = lines.index("└── README.md")

    assert src_index < gitignore_index
    assert gitignore_index < readme_index
