"""Verify the file-organizer Harness source is consolidated under harness/mcp."""

from harness.mcp import file_organizer_server, mcp_harness_server


def test_file_organizer_entry_points_reuse_relocated_harness_server() -> None:
    assert file_organizer_server.mcp is mcp_harness_server.mcp
