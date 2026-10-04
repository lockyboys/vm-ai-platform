from engine.intelligence.pre_identity_intelligence import PreIdentityIntelligence


def test_pre_identity_requires_repository_evidence_instead_of_fixed_defaults():
    result = PreIdentityIntelligence().decide("DOCUMENT", {})

    assert result["status"] == "NEEDS_EVIDENCE"
    assert result["confidence"] == 0.0
    assert result["book_policy"] == "UNRESOLVED"
    assert result["book_version_policy"] == "UNRESOLVED"
    assert result["read_session_policy"] == "UNRESOLVED"


def test_unverified_input_cannot_select_create_new_policy_or_override_object_code():
    result = PreIdentityIntelligence().decide(
        "DOCUMENT",
        {
            "pre_identity_evidence": {
                "verified_yn": False,
                "object_code": "ATTACKER_VALUE",
                "book_policy": "CREATE_NEW",
            }
        },
    )

    assert result["status"] == "NEEDS_EVIDENCE"
    assert result["object_code"] == "DOCUMENT"
    assert result["book_policy"] == "UNRESOLVED"


def test_only_verified_complete_policy_fields_are_returned():
    result = PreIdentityIntelligence().decide(
        "DOCUMENT",
        {
            "pre_identity_evidence": {
                "verified_yn": True,
                "object_code": "ATTACKER_VALUE",
                "status": "OVERRIDE",
                "book_policy": "REUSE",
                "book_id_policy": "USE_EXISTING",
                "book_version_policy": "REUSE",
                "book_version_id_policy": "USE_EXISTING",
                "read_session_policy": "CREATE_NEW",
                "read_session_id_policy": "GENERATE",
                "knowledge_unit_policy": "PARAGRAPH",
            }
        },
    )

    assert result["status"] == "SUCCESS"
    assert result["object_code"] == "DOCUMENT"
    assert result["book_policy"] == "REUSE"
    assert result["knowledge_unit_policy"] == "PARAGRAPH"
