"""MongoDB storage-separation verification helper tests."""

from scripts.verify_impact_analysis_storage_separation import _payload_field_names


def test_payload_field_names_returns_all_nested_payload_fields() -> None:
    assert _payload_field_names(
        {
            "payload": {
                "sp_impact_analysis_text": {
                    "change_target_text": "target",
                    "affected_text": "affected",
                }
            }
        }
    ) == ["affected_text", "change_target_text"]


def test_payload_field_names_returns_empty_for_missing_payload() -> None:
    assert _payload_field_names({}) == []
