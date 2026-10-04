from __future__ import annotations

import pytest

from harness.mcp.tools import model_history_audit_ddl_tool as ddl


class _FakeDatabase:
    def __init__(self, database_role: str) -> None:
        self.database_role = database_role
        self.database_name = "te_common"
        self.executed: list[str] = []
        self.exists = True
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def fetch_one(self, sql: str, params=None):
        if "information_schema.tables" in sql:
            if self.exists:
                return {"table_name": params[-1], "table_type": "BASE TABLE"}
            return None
        raise AssertionError(sql)

    def execute(self, sql: str) -> int:
        self.executed.append(sql)
        if sql.upper().startswith("DROP TABLE"):
            self.exists = False
        return 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def _fake(monkeypatch):
    fake = _FakeDatabase("COMMON")
    monkeypatch.setattr(ddl, "CommonDatabase", lambda **kwargs: fake)
    return fake


def test_ddl_dry_run_previews_drop_without_execution(monkeypatch) -> None:
    fake = _fake(monkeypatch)
    result = ddl.mariadb_ddl_execute(
        "DROP TABLE model_history",
        confirmation_text="DROP TABLE te_common.model_history",
    )
    assert result["dry_run"] is True
    assert result["operation"] == "DROP"
    assert fake.executed == []
    assert fake.closed is True


def test_drop_requires_exact_confirmation(monkeypatch) -> None:
    fake = _fake(monkeypatch)
    with pytest.raises(ValueError, match="DROP requires confirmation_text"):
        ddl.mariadb_ddl_execute("DROP TABLE model_history", apply=True)
    assert fake.executed == []
    assert fake.rollbacks == 1


def test_drop_apply_executes_one_table_and_verifies_absence(monkeypatch) -> None:
    fake = _fake(monkeypatch)
    result = ddl.mariadb_ddl_execute(
        "DROP TABLE model_history",
        apply=True,
        confirmation_text="DROP TABLE te_common.model_history",
    )
    assert result["applied"] is True
    assert result["verified_absent"] is True
    assert fake.executed == ["DROP TABLE model_history"]
    assert fake.commits == 1


@pytest.mark.parametrize(
    "sql_text",
    [
        "DROP DATABASE te_common",
        "DROP TABLE model_history, cm_code",
        "ALTER TABLE model_history ADD x INT; DROP TABLE model_history",
        "ALTER TABLE other_db.model_history ADD x INT",
        "DROP TABLE model_history -- comment",
    ],
)
def test_rejects_unsafe_or_out_of_scope_ddl(monkeypatch, sql_text: str) -> None:
    _fake(monkeypatch)
    with pytest.raises(ValueError):
        ddl.mariadb_ddl_execute(sql_text, apply=True, confirmation_text="DROP TABLE te_common.model_history")


def test_alter_table_apply_is_supported_and_committed(monkeypatch) -> None:
    fake = _fake(monkeypatch)
    result = ddl.mariadb_ddl_execute(
        "ALTER TABLE model_history ADD COLUMN example_col INT",
        apply=True,
    )
    assert result["operation"] == "ALTER"
    assert result["applied"] is True
    assert fake.executed == ["ALTER TABLE model_history ADD COLUMN example_col INT"]
    assert fake.commits == 1

def test_truncate_requires_exact_confirmation(monkeypatch) -> None:
    fake = _fake(monkeypatch)
    with pytest.raises(ValueError, match="TRUNCATE requires confirmation_text"):
        ddl.mariadb_ddl_execute("TRUNCATE TABLE model_history", apply=True)
    assert fake.executed == []
    assert fake.rollbacks == 1


@pytest.mark.parametrize("sql_text", ["TRUNCATE model_history", "TRUNCATE TABLE model_history"])
def test_truncate_apply_executes_only_with_exact_confirmation(monkeypatch, sql_text: str) -> None:
    fake = _fake(monkeypatch)
    result = ddl.mariadb_ddl_execute(
        sql_text,
        apply=True,
        confirmation_text="TRUNCATE TABLE te_common.model_history",
    )
    assert result["operation"] == "TRUNCATE"
    assert result["applied"] is True
    assert fake.executed == [sql_text]
    assert fake.commits == 1
