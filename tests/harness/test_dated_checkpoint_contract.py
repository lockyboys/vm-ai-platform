"""Dated checkpoint source contract regression tests."""
from pathlib import Path


SOURCE = Path("harness/mcp/sps_harness_server.py")


def test_checkpoint_source_compiles_and_uses_kst_dated_files():
    # Verify the server loads and maps checkpoint writes to Korea's workday.
    text = SOURCE.read_text(encoding="utf-8")
    compile(text, str(SOURCE), "exec")
    assert 'f"current_{kst_now:%Y%m%d}.md"' in text
    assert 'ZoneInfo("Asia/Seoul")' in text
    assert 'Checkpoint updated at:' in text


def test_legacy_current_file_is_read_only_fallback():
    # A dated file is primary; current.md remains only a temporary read fallback.
    text = SOURCE.read_text(encoding="utf-8")
    update_segment = text[text.index("def update_current_checkpoint"):text.index("@mcp.tool()", text.index("def update_current_checkpoint") + 1)]
    assert '_dated_checkpoint_file()' in update_segment
    assert '"current.md"' not in update_segment
