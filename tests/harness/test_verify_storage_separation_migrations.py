from harness.scripts.verify_storage_separation_migrations import _has_payload_value


def test_has_payload_value_treats_only_null_and_empty_string_as_cleared() -> None:
    assert _has_payload_value(None) is False
    assert _has_payload_value("") is False
    assert _has_payload_value(" ") is True
    assert _has_payload_value("detail") is True
    assert _has_payload_value({"field": "value"}) is True
