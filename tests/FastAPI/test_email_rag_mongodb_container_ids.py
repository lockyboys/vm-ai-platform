"""LangGraph_email_RAG_Agent의 MongoDB 상위 계층 ID(MDB/MCO) 해석 검증 테스트.

목적
- 보험 PDF 문서에 저장하는 mongodb_database_id, mongodb_collection_id가
  소스 고정값(하드코딩)이 아니라 Repository(sp_object)에서 해석되는지 확인한다.
- Repository에 활성 Object가 없을 때(잘못된 입력) 조용히 기본값으로
  넘어가지 않고 RuntimeError로 중단하는지 확인한다.

배경
- 2026-10-24 이전 소스는 os.getenv("MONGODB_DATABASE_ID", "SP_RP_MDB_2026_00001")처럼
  Object ID를 기본값으로 박아 두어 Repository First/No Hardcoding 원칙에 어긋났다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# 테스트 대상 소스 파일 경로(프로젝트 루트 기준).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_AGENT_SOURCE = _PROJECT_ROOT / "FastAPI" / "LangGraph" / "Agent_Import_RAGs" / "LangGraph_email_RAG_Agent.py"


class _RepositoryDouble:
    """sp_object 조회만 흉내 내는 테스트 대역.

    objects: object_code -> object_id 매핑. 매핑에 없는 코드는 None(미등록)을 돌려준다.
    calls: 어떤 object_code로 조회했는지 기록해 Repository 조회 여부를 검증한다.
    """

    def __init__(self, objects: dict[str, str]):
        self.objects = objects
        self.calls: list[str] = []

    def fetch_one(self, sql, params):
        # 소스가 sp_object를 조회하는지 SQL 문자열로 확인한다.
        assert "FROM sp_object" in sql
        object_code = params[0]
        self.calls.append(object_code)
        object_id = self.objects.get(object_code)
        return None if object_id is None else {"object_id": object_id, "object_code": object_code}


def _load_helper():
    """테스트 대상 helper를 import한다(모듈 import 실패 시 원인 그대로 노출)."""
    from FastAPI.LangGraph.Agent_Import_RAGs.LangGraph_email_RAG_Agent import (
        _load_mongodb_container_ids,
    )

    return _load_mongodb_container_ids


def test_source_has_no_hardcoded_mongodb_container_ids():
    """문제 재현: 소스에 MDB/MCO Object ID 고정값이 남아 있으면 실패한다."""
    source_text = _AGENT_SOURCE.read_text(encoding="utf-8")
    assert "SP_RP_MDB_2026_00001" not in source_text
    assert "SP_RP_MCO_202608_00001" not in source_text


def test_container_ids_are_resolved_from_repository():
    """정상 입력: sp_object의 MDB/MCO object_id를 그대로 돌려준다."""
    load_ids = _load_helper()
    repository = _RepositoryDouble({"MDB": "SP_RP_MDB_2026_00001", "MCO": "SP_RP_MCO_202608_00001"})

    result = load_ids(repository)

    assert result == {
        "mongodb_database_id": "SP_RP_MDB_2026_00001",
        "mongodb_collection_id": "SP_RP_MCO_202608_00001",
    }
    assert repository.calls == ["MDB", "MCO"]


@pytest.mark.parametrize("missing_code", ["MDB", "MCO"])
def test_missing_repository_object_raises(missing_code):
    """잘못된 입력: 활성 Object가 없으면 기본값 없이 RuntimeError로 중단한다."""
    load_ids = _load_helper()
    objects = {"MDB": "SP_RP_MDB_2026_00001", "MCO": "SP_RP_MCO_202608_00001"}
    objects.pop(missing_code)

    with pytest.raises(RuntimeError, match=missing_code):
        load_ids(_RepositoryDouble(objects))
