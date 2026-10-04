class PreIdentityIntelligence:
    """
    Pre-Identity Intelligence

    Identifier 생성 전에 기존 식별자 여부를 확인한다.
    Repository 증거가 없으면 정책을 확정하지 않는다.
    """

    _POLICY_FIELDS = (
        "book_policy",
        "book_id_policy",
        "book_version_policy",
        "book_version_id_policy",
        "read_session_policy",
        "read_session_id_policy",
        "knowledge_unit_policy",
    )

    def decide(self, object_code, input_context=None):
        input_context = input_context or {}
        evidence = input_context.get("pre_identity_evidence")
        verified = isinstance(evidence, dict) and evidence.get("verified_yn") is True
        complete = verified and all(evidence.get(key) for key in self._POLICY_FIELDS)

        if not complete:
            return {
                "intelligence_type": "PRE_IDENTITY_INTELLIGENCE",
                "object_code": object_code,
                **{key: "UNRESOLVED" for key in self._POLICY_FIELDS},
                "confidence": 0.0,
                "reason": "Book, Version, Read Session Repository 증거가 없거나 불완전합니다.",
                "status": "NEEDS_EVIDENCE",
            }

        # 검증된 정책 필드만 복사해 호출자 입력이 결과 식별자나 상태를 덮지 않게 한다.
        verified_policies = {
            key: evidence[key]
            for key in self._POLICY_FIELDS
        }
        return {
            "intelligence_type": "PRE_IDENTITY_INTELLIGENCE",
            "object_code": object_code,
            **verified_policies,
            "confidence": 1.0,
            "reason": "검증된 Pre-Identity Repository 증거를 사용했습니다.",
            "status": "SUCCESS",
        }
