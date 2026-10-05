"""Install and verify tiktoken in the active SPS Python environment."""

import subprocess
import sys


def main() -> int:
    # Install into the same interpreter environment that executes this script.
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "tiktoken==0.14.0"],
        check=True,
    )

    # Confirm the package version and expected model-to-encoding mapping.
    verify = (
        "import tiktoken; "
        "print(tiktoken.__version__, "
        "tiktoken.encoding_for_model('gpt-5.6-luna').name)"
    )
    subprocess.run([sys.executable, "-c", verify], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
