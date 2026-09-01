# =============================================================================
# File Name   : harness/mcp/mcp_harness_server.py
# Purpose     : 파일을 정리하는 기능만 따로 제공하는 작은 MCP 서버
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260902 | Codex | Harness 표준 파일 헤더와 선택적 Organizer 로딩 역할을 보강했음
# =============================================================================
# 이 파일은 무엇을 하나요?
# - 사용자가 고른 폴더의 파일을 정리하고, 컴퓨터 상태를 확인하는 기능을 제공합니다.
# - 파일 정리 기능이 필요할 때만 관련 모듈을 불러와서 기본 Harness 시작을 방해하지 않습니다.
# 주의: common_function.py의 공통 검사 기능을 사용하며, 없는 폴더는 정리하지 않습니다.
from importlib import import_module

from mcp.server.fastmcp import FastMCP

from common import common_function as utils

mcp = FastMCP("SPS-File-Organizer-Harness")


def _load_main_organizer():
    """Load the optional file-organizer runtime only when its tool is invoked."""
    try:
        return import_module("main_organizer")
    except ModuleNotFoundError as error:
        if error.name != "main_organizer":
            raise
        raise RuntimeError(
            "main_organizer module is not available in this SPS project."
        ) from error


@mcp.tool()
def organize_directory(directory_path: str) -> str:
    """Organize the selected directory through the legacy organizer runtime."""
    validated_path = utils.validate_path(directory_path)
    if not validated_path:
        return f"❌ 오류: '{directory_path}' 경로는 존재하지 않거나 유효하지 않습니다."

    try:
        organizer = _load_main_organizer()
        organizer.run_total_organization(str(validated_path))
        return f"✅ 성공: '{directory_path}' 경로의 파일 지능형 분류 정리가 완료되었습니다."
    except Exception as error:
        return f"❌ 정리 실행 중 오류 발생: {error}"


@mcp.tool()
def check_system_status() -> str:
    """Return the legacy file-organizer environment status."""
    try:
        return utils.get_system_status()
    except Exception as error:
        return f"❌ 시스템 진단 중 오류 발생: {error}"


if __name__ == "__main__":
    mcp.run()
