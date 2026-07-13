"""
SPS Relationship Runtime Adapter

Input:
    outputs/identifier_blueprint_relationship_request.json

Output:
    outputs/identifier_blueprint_relationship_result.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from engine.generator.relationship_generator import (
    RelationshipGenerator,
)


DEFAULT_REQUEST_PATH = Path(
    "outputs/identifier_blueprint_relationship_request.json"
)

DEFAULT_RESULT_PATH = Path(
    "outputs/identifier_blueprint_relationship_result.json"
)


def load_request(
    request_path: Path,
) -> list[dict[str, Any]]:
    """Relationship Request JSON을 읽는다."""
    if not request_path.exists():
        raise FileNotFoundError(
            f"Request file not found: {request_path}"
        )

    payload = json.loads(
        request_path.read_text(encoding="utf-8")
    )

    if not isinstance(payload, dict):
        raise ValueError(
            "Relationship Runtime payload must be a JSON object."
        )

    relationships = payload.get("relationships")

    if not isinstance(relationships, list):
        raise ValueError(
            "'relationships' must be a JSON array."
        )

    return relationships


def save_result(
    result: dict[str, Any],
    result_path: Path,
) -> None:
    """Runtime 결과를 JSON으로 저장한다."""
    result_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


def main() -> int:
    load_dotenv("/data/vm_project/.env")

    request_path = (
        Path(sys.argv[1])
        if len(sys.argv) >= 2
        else DEFAULT_REQUEST_PATH
    )

    result_path = (
        Path(sys.argv[2])
        if len(sys.argv) >= 3
        else DEFAULT_RESULT_PATH
    )

    print("=" * 70)
    print("SPS Relationship Runtime")
    print("=" * 70)
    print(f"Request : {request_path}")
    print(f"Result  : {result_path}")
    print("-" * 70)

    try:
        relationships = load_request(request_path)

        print("[STEP-001] Relationship Request Loaded")
        print(f"Count : {len(relationships)}")

        print("[STEP-002] Predicate Metadata Validation")
        print("[STEP-003] Object Type Metadata Validation")
        print("[STEP-004] Source/Target Repository Validation")
        print("[STEP-005] Relationship Identifier Generation")
        print("[STEP-006] Relationship Repository Save")
        print("[STEP-007] Transaction Commit")

        generator = RelationshipGenerator()
        result = generator.create_batch(relationships)

        save_result(result, result_path)

        print("-" * 70)
        print(f"Status  : {result.get('status')}")
        print(f"Success : {result.get('success')}")
        print(
            f"Count   : "
            f"{result.get('relationship_count', 0)}"
        )
        print(f"Message : {result.get('message')}")

        for relationship in result.get(
            "relationships",
            [],
        ):
            print("-" * 70)
            print(
                f"ID        : "
                f"{relationship['relationship_id']}"
            )
            print(
                f"Source    : "
                f"{relationship['source_object_id']}"
            )
            print(
                f"Predicate : "
                f"{relationship['relationship_type_code']}"
            )
            print(
                f"Target    : "
                f"{relationship['target_object_id']}"
            )

        print("=" * 70)

        return 0 if result.get("success") else 1

    except Exception as exc:
        result = {
            "success": False,
            "status": "FAILED",
            "message": str(exc),
            "exception_type": type(exc).__name__,
        }

        save_result(result, result_path)

        print("-" * 70)
        print("Status  : FAILED")
        print(f"Message : {exc}")
        print("=" * 70)

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
