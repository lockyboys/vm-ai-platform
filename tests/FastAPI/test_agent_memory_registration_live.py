"""Read-only preflight for agent_long_term_memory Repository registration."""
from harness.scripts.register_agent_long_term_memory import register
from harness.scripts.verify_agent_long_term_memory import verify


def test_agent_memory_registration_preflight():
    preview = register(apply=False)
    assert preview["applied"] is False
    assert preview["erd_id"]
    assert "_id" in preview["attribute_names"]
    assert "sp_object_execution_link" in preview["schema_column_counts"]

def test_agent_memory_verifier_is_read_only():
    state = verify()
    assert "mongodb_document_count" in state
    assert state["registration_complete_yn"] in {"Y", "N"}
    assert state["live_write_verified_yn"] in {"Y", "N"}
