from src.common.formatter import FormatterConfig, PrettyOutput


def test_title_only_output() -> None:
    output = PrettyOutput(
        "Git Status",
        config=FormatterConfig(width=60),
    )

    result = output.render()

    assert "🌿 Git Status" in result
    assert "SUCCESS" in result


def test_summary_output() -> None:
    output = PrettyOutput("Source Search").summary(
        Keyword="identifier",
        Found=3,
    )

    result = output.render()

    assert "📄 Source Search" in result
    assert "Keyword" in result
    assert "identifier" in result
    assert "Found" in result
    assert "3" in result


def test_table_output() -> None:
    output = PrettyOutput("Table Data").table(
        columns=["ID", "Name"],
        rows=[
            [1, "Alpha"],
            [2, "Beta"],
        ],
    )

    result = output.render()

    assert "📊 Table Data" in result
    assert "Alpha" in result
    assert "Beta" in result


def test_custom_icon() -> None:
    output = PrettyOutput(
        "Custom Tool",
        icon="🚀",
    )

    result = output.render()

    assert "🚀 Custom Tool" in result


def test_empty_title_validation() -> None:
    try:
        PrettyOutput(" ")
    except ValueError as exc:
        assert "title must not be empty" in str(exc)
    else:
        raise AssertionError("ValueError was not raised.")


def test_tree_output() -> None:
    output = PrettyOutput(
        "Git Status"
    )

    output.summary(
        Modified=2,
        Untracked=1,
    )

    output.tree(
        title="Modified",
        paths=[
            ".gitignore",
            "src/common/formatter/pretty_output.py",
        ],
    )

    rendered = output.render()

    assert "Modified" in rendered
    assert "." in rendered
    assert "src/" in rendered
    assert "common/" in rendered
    assert "formatter/" in rendered
    assert "pretty_output.py" in rendered
    assert ".gitignore" in rendered


def test_multiple_tree_output() -> None:
    output = PrettyOutput(
        "Git Status"
    )

    output.tree(
        title="Modified",
        paths=[
            "src/common/file.py",
        ],
    )

    output.tree(
        title="Untracked",
        paths=[
            "tests/common/test_file.py",
        ],
    )

    rendered = output.render()

    assert "Modified" in rendered
    assert "Untracked" in rendered
    assert "src/" in rendered
    assert "tests/" in rendered


def test_tree_title_validation() -> None:
    output = PrettyOutput(
        "Git Status"
    )

    try:
        output.tree(
            title="",
            paths=[
                "src/common/file.py",
            ],
        )
    except ValueError as error:
        assert (
            str(error)
            == "Tree title must not be empty."
        )
    else:
        raise AssertionError(
            "ValueError was not raised."
        )
