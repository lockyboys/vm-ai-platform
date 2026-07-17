from src.common.formatter import (
    FormatterConfig,
    PrettyFormatter,
    RenderModel,
    TableModel,
)


def test_pretty_formatter_render() -> None:
    formatter = PrettyFormatter(
        FormatterConfig(width=60)
    )

    model = RenderModel(
        title="Table Schema",
        icon="🗂",
        summary={
            "Table": "cm_common_code",
            "Columns": 3,
            "Result": "SUCCESS",
        },
        table=TableModel(
            columns=[
                "Column",
                "Type",
                "Nullable",
            ],
            rows=[
                [
                    "group_code",
                    "VARCHAR(100)",
                    "NO",
                ],
                [
                    "code",
                    "VARCHAR(100)",
                    "NO",
                ],
                [
                    "common_code_json",
                    "JSON",
                    "YES",
                ],
            ],
        ),
        status="SUCCESS",
    )

    result = formatter.render(model)

    assert "🗂 Table Schema" in result
    assert "cm_common_code" in result
    assert "common_code_json" in result
    assert "SUCCESS" in result


def test_table_column_count_validation() -> None:
    formatter = PrettyFormatter()

    model = RenderModel(
        title="Invalid Table",
        table=TableModel(
            columns=["Column", "Type"],
            rows=[
                ["column_only"],
            ],
        ),
    )

    try:
        formatter.render(model)
    except ValueError as exc:
        assert "column count mismatch" in str(exc)
    else:
        raise AssertionError("ValueError was not raised.")
