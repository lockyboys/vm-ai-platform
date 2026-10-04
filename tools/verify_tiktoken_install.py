"""Install and verify the requested tokenizer in the active SPS Python environment."""

import subprocess
import sys


def main() -> int:
    # Use this script's interpreter so pip installs into the active project venv.
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "tiktoken==0.14.0"],
        check=True,
    )

    # Verify both the installed package version and the requested model mapping.
    verify = (
        "import tiktoken; "
        "print(tiktoken.__version__, "
        "tiktoken.encoding_for_model('gpt-5.6-luna').name)"
    )
    subprocess.run([sys.executable, "-c", verify], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
