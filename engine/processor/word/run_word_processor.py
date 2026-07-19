"""Run SPS Repository Table Schema Word Processor."""

from __future__ import annotations

import argparse
from pathlib import Path

from engine.processor.word.word_document_processor import (
    WordDocumentProcessor,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Repository Table Schema를 Word Artifact로 생성합니다."
        )
    )
    parser.add_argument(
        "table_name",
        nargs="?",
        default="cm_common_code",
    )
    parser.add_argument(
        "--database-role",
        default="COMMON",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--output",
        default=None,
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    output_path = (
        Path(arguments.output)
        if arguments.output
        else Path("output")
        / f"{arguments.table_name}_schema.docx"
    )

    processor = WordDocumentProcessor(
        database_role=arguments.database_role,
    )

    try:
        result = processor.generate_table_document(
            table_name=arguments.table_name,
            output_path=output_path,
            sample_limit=arguments.sample_limit,
        )

        print("=" * 80)
        print("SPS Table Schema Word Generation SUCCESS")
        print("=" * 80)
        print(f"Table  : {arguments.table_name}")
        print(f"Output : {result.resolve()}")
        print("=" * 80)
    finally:
        processor.database.close()


if __name__ == "__main__":
    main()
