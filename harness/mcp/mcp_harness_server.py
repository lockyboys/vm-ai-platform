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
