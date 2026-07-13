"""
SPS Metadata Runtime Adapter
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.generator.metadata_generator import MetadataGenerator


REQUEST_PATH = Path(
    "outputs/metadata_forbidden_request.json"
)
RESULT_PATH = Path(
    "outputs/metadata_forbidden_result.json"
)


def main() -> None:
    """Metadata Request를 실행한다."""
    print("=" * 70)
    print("SPS Metadata Runtime")
    print("=" * 70)
    print(f"Request : {REQUEST_PATH}")
    print(f"Result  : {RESULT_PATH}")
    print("-" * 70)

    try:
        request_data = json.loads(
            REQUEST_PATH.read_text(encoding="utf-8")
        )

        metadata_requests = request_data["metadata"]

        print("[STEP-001] Metadata Request Loaded")
        print(f"Count : {len(metadata_requests)}")

        generator = MetadataGenerator()

        print("[STEP-002] Metadata Identifier Generation")
        print("[STEP-003] Metadata Repository Save")
        print("[STEP-004] Transaction Commit")

        result = generator.create_batch(
            metadata_requests
        )

        RESULT_PATH.write_text(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                default=str,
            ) + "\n",
            encoding="utf-8",
        )

        print("-" * 70)
        print(f"Status  : {result['status']}")
        print(f"Success : {result['success']}")
        print(
            "Count   : "
            f"{result.get('metadata_count', 0)}"
        )
        print(f"Message : {result['message']}")
        print("=" * 70)

    except Exception as exc:
        result = {
            "success": False,
            "status": "FAILED",
            "message": str(exc),
        }

        RESULT_PATH.write_text(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

        print("-" * 70)
        print("Status  : FAILED")
        print(f"Message : {exc}")
        print("=" * 70)


if __name__ == "__main__":
    main()
