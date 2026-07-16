"""
SPS Object Definition Runtime Adapter

Input:
    outputs/object_definition_request.json

Output:
    outputs/object_definition_result.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from engine.object_definition import (
    ObjectDefinitionEngine,
)


DEFAULT_REQUEST_PATH = Path(
    "outputs/object_definition_request.json"
)

DEFAULT_RESULT_PATH = Path(
    "outputs/object_definition_result.json"
)


def load_request(
    request_path: Path,
) -> dict[str, Any]:
    """Object Definition Request JSON을 읽는다."""
    if not request_path.exists():
        raise FileNotFoundError(
            f"Request file not found: {request_path}"
        )

    data = json.loads(
        request_path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            "Object Definition Request must be a JSON object."
        )

    return data


def save_result(
    result: dict[str, Any],
    result_path: Path,
) -> None:
    """Generator 실행 결과를 JSON으로 저장한다."""
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
    print("SPS Object Definition Runtime")
    print("=" * 70)
    print(f"Request : {request_path}")
    print(f"Result  : {result_path}")
    print("-" * 70)

    try:
        request = load_request(request_path)

        print("[STEP-001] Request Loaded")
        print(f"Object Code : {request.get('object_code')}")

        generator = ObjectDefinitionEngine()

        print("[STEP-002] Repository Validation")
        print("[STEP-003] Identifier Sequence")
        print("[STEP-004] Object Identifier")
        print("[STEP-005] Repository Save")

        result = generator.create(request)

        save_result(result, result_path)

        print("-" * 70)
        print(f"Status    : {result.get('status')}")
        print(f"Success   : {result.get('success')}")
        print(f"Object ID : {result.get('object_id')}")
        print(f"Message   : {result.get('message')}")
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
