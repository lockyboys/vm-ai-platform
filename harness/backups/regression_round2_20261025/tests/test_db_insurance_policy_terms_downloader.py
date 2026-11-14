"""(대체됨) DB손보 전용 수집기 테스트.

2026-10-24 사용자 지시(특정 사이트 커스터마이징 금지)로 사이트 전용 수집기는 만들지 않고
일반 엔진 public_document_catalog_collector.py + profiles/db_insurance_terms.json으로 대체했다.
검증은 tests/test_public_document_catalog_collector.py에서 한다.
source_delete는 추적되지 않은 파일을 지울 수 없어 이 파일을 건너뛰기로 남긴다(삭제는 사용자 판단).
"""
import pytest

pytest.skip("superseded by tests/test_public_document_catalog_collector.py", allow_module_level=True)
