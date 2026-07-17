from __future__ import annotations

from harness.mcp.tools.pytest_tools import (
    run_pytest_verification,
)


def main() -> int:
    result = run_pytest_verification(
        [
            "tests/common/formatter",
        ],
        title="Formatter Framework Verification",
    )

    print(
        result["pretty_output"]
    )

    return int(
        result["exit_code"]
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
