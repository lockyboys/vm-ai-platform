"""Compatibility import for the relocated file-organizer Harness server."""

from harness.mcp.mcp_harness_server import mcp


if __name__ == "__main__":
    mcp.run()
