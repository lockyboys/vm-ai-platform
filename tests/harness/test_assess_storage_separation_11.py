from harness.scripts.assess_storage_separation_11 import TARGETS, _quote


def test_manifest_has_all_eleven_unique_source_tables() -> None:
    assert len(TARGETS) == 11
    assert len({target[1] for target in TARGETS}) == 11


def test_quote_accepts_only_safe_identifiers() -> None:
    assert _quote("cm_repository") == "`cm_repository`"
