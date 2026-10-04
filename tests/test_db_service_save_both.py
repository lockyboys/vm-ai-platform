"""save_both의 성공·부분 실패 전파 계약을 검증한다."""

import pytest

from services.db import db_service


def test_save_both_returns_success_only_when_both_stores_succeed(monkeypatch):
    """두 저장소가 성공하면 기존 반환 계약을 유지한다."""
    monkeypatch.setattr(db_service, "save_to_mongo", lambda collection, data: True)
    monkeypatch.setattr(db_service, "save_to_mysql", lambda table, data: True)

    assert db_service.save_both("pipeline_results", {"value": 1}) == {
        "MongoDB": "성공",
        "MariaDB": "성공",
    }


@pytest.mark.parametrize(
    ("mongo_result", "maria_result"),
    [
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_save_both_raises_when_any_store_reports_failure(
    monkeypatch, mongo_result, maria_result
):
    """어느 저장소든 실패하면 성공 상태를 반환하지 않고 호출자를 중단시킨다."""
    monkeypatch.setattr(db_service, "save_to_mongo", lambda collection, data: mongo_result)
    monkeypatch.setattr(db_service, "save_to_mysql", lambda table, data: maria_result)

    with pytest.raises(RuntimeError, match="Pipeline 저장 실패"):
        db_service.save_both("pipeline_results", {"value": 1})


def test_save_both_attempts_second_store_when_first_raises(monkeypatch):
    """첫 저장소 예외가 발생해도 양쪽 시도를 마친 뒤 최종 실패를 전파한다."""
    calls = []

    def fail_mongo(collection, data):
        calls.append("MongoDB")
        raise OSError("secret connection details")

    def save_maria(table, data):
        calls.append("MariaDB")
        return True

    monkeypatch.setattr(db_service, "save_to_mongo", fail_mongo)
    monkeypatch.setattr(db_service, "save_to_mysql", save_maria)

    with pytest.raises(RuntimeError, match="OSError") as error:
        db_service.save_both("pipeline_results", {"value": 1})

    assert calls == ["MongoDB", "MariaDB"]
    assert "secret connection details" not in str(error.value)
