from harness.scripts.drop_storage_separation_payload_columns import TARGETS


def test_drop_manifest_covers_all_eleven_tables() -> None:
    assert len(TARGETS) == 11
    assert all(target[2].endswith(("20260830", "20260902")) for target in TARGETS)
