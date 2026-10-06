"""Authenticated SPDS desktop application entry point."""

from __future__ import annotations

import os
import sys

from config import BASE_DIR
from dotenv import load_dotenv

# Load the shared root configuration before constructing CommonAuth/Database.
load_dotenv(BASE_DIR / ".env", override=False)

from common.auth import CommonAuth
from common.common_function import logger
from PySide6.QtWidgets import QApplication
from spds.ui.main_window import MainWindow


def main() -> int:
    """Start SPDS only with a valid signed access token."""
    token = os.getenv("SPS_UI_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SPS_UI_ACCESS_TOKEN 환경변수가 필요합니다.")

    # The signed subject is checked again against active COMMON.cm_member by the runtime.
    claims = CommonAuth().verify_token(token, expected_type="access")
    member_id = str(claims.get("sub") or "").strip()
    if not member_id:
        raise RuntimeError("검증된 Access Token에 Member ID가 없습니다.")

    app = QApplication(sys.argv)
    window = MainWindow(member_id=member_id)
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logger.error("SPDS startup failed: %s", exc)
        raise SystemExit(1) from exc
