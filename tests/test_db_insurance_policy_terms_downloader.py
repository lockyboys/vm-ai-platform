"""대체된 사이트 전용 테스트 대신 배포 프로파일과 공통 수집기의 연결을 검증한다."""
import json
from pathlib import Path

from FastAPI.LangGraph.Agent_Import_PFDs import public_document_catalog_collector as collector


def test_shipped_db_profile_uses_general_collector_contract():
    """실제 배포 프로파일을 공통 엔진에 전달한다. 네트워크·다운로드는 실행하지 않는다."""
    root = Path(__file__).resolve().parents[1]
    path = root / "FastAPI/LangGraph/Agent_Import_PFDs/profiles/db_insurance_terms.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    assert collector.validate_profile(profile)["name"] == profile["name"]
