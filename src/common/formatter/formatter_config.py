from dataclasses import dataclass


@dataclass(frozen=True)
class FormatterConfig:
    """Pretty Formatter 출력 설정."""

    width: int = 80
    header_character: str = "="
    divider_character: str = "─"
    key_value_separator: str = " : "
    table_column_separator: str = " │ "
    empty_value: str = "-"
    success_text: str = "SUCCESS"
    warning_text: str = "WARNING"
    error_text: str = "ERROR"
    info_text: str = "INFO"
