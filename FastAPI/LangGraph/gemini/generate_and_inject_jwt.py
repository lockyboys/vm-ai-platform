"""Issue an SPS access token through the shared protected CommonAuth key.

Purpose: keep compatibility with the old helper while eliminating a local JWT
signing key. The token is returned to the caller and is never printed or stored
in source; callers must keep it in memory and avoid logging it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.auth import CommonAuth


def generate_and_inject_jwt(user_id: str = "jeaje") -> str:
    """Create one short-lived CommonAuth access token for the requested user."""
    token = CommonAuth().issue_access_token(user_id)
    os.environ["SPS_MCP_BEARER_TOKEN"] = token
    return token


if __name__ == "__main__":
    # Do not print the bearer credential when this helper is run directly.
    generate_and_inject_jwt()
