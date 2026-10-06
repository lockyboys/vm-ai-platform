from __future__ import annotations

import pytest

from spds.ui.ui_runtime import UIRuntimeConfigurationError, UIRuntimeRepository


class FakeDatabase:
    """Provide Repository-shaped rows without opening MariaDB in unit tests."""

    def __init__(self, *, member_exists: bool = True, screen_id_column: bool = True):
        self.member_exists = member_exists
        self.screen_id_column = screen_id_column
        self.object_rows = [
            {
                "code": "SP_UI_SCREEN",
                "common_code_json": {
                    "object_code": "SP_UI_SCREEN",
                    "object_level": 3,
                    "target_identifier_field": "ui_screen_id",
                },
            },
            *[
                {"code": code, "common_code_json": {"object_code": code}}
                for code in ("SP_UI_MENU", "SP_UI_ACTION", "SP_UI_PERMISSION")
            ],
        ]
        self.code_rows = [
            {"group_code": "UI_SCREEN_TYPE", "code": "LIST"},
            {"group_code": "UI_MENU_TYPE", "code": "ITEM"},
            {"group_code": "UI_MENU_TYPE", "code": "GROUP"},
            {"group_code": "UI_ACTION_TYPE", "code": "READ"},
            {"group_code": "UI_ACTION_TYPE", "code": "UPDATE"},
            {"group_code": "UI_PERMISSION_TYPE", "code": "READ"},
            {"group_code": "UI_PERMISSION_TYPE", "code": "UPDATE"},
            {"group_code": "UI_PERMISSION_SUBJECT_TYPE", "code": "MEMBER"},
            {"group_code": "UI_PERMISSION_SUBJECT_TYPE", "code": "RULE"},
        ]
        self.menu_rows = [
            {
                "menu_code": "MENU_REPORT",
                "ui_screen_id": "SCREEN_REPORT",
                "menu_name": "Reports",
                "menu_url": "/reports",
                "ui_screen_type_code": "LIST",
                "ui_menu_type_code": "ITEM",
                "menu_sort_no": 10,
            }
        ]
        self.action_rows = [
            {
                "button_code": "REPORT_READ",
                "menu_code": "MENU_REPORT",
                "button_name": "View report",
                "ui_action_type_code": "READ",
                "query_id": "QUERY_REPORT_READ",
                "button_sort_no": 10,
            },
            {
                "button_code": "REPORT_UPDATE",
                "menu_code": "MENU_REPORT",
                "button_name": "Update report",
                "ui_action_type_code": "UPDATE",
                "query_id": "QUERY_REPORT_UPDATE",
                "button_sort_no": 20,
            },
        ]
        self.member_rule_rows = []
        self.permission_rows = [
            {
                "button_code": "REPORT_READ",
                "permission_subject_type_code": "MEMBER",
                "permission_subject_id": "member-1",
                "permission_type_code": "READ",
            },
            {
                "button_code": "REPORT_UPDATE",
                "permission_subject_type_code": "MEMBER",
                "permission_subject_id": "member-2",
                "permission_type_code": "UPDATE",
            },
        ]

    def fetch_one(self, sql: str, params=None):
        if "information_schema.columns" in sql:
            return {"column_count": int(self.screen_id_column)}
        if "FROM cm_member" in sql:
            return {"member_id": params[0]} if self.member_exists else None
        raise AssertionError(f"Unexpected fetch_one query: {sql}")

    def fetch_all(self, sql: str, params=None):
        if "FROM cm_member_role AS member_role" in sql:
            return self.member_rule_rows
        if "SELECT code, common_code_json" in sql:
            return self.object_rows
        if "group_code IN" in sql:
            return self.code_rows
        if "FROM ui_menu AS m" in sql:
            return self.menu_rows
        if "FROM ui_menu_action AS a" in sql:
            return self.action_rows
        if "FROM ui_menu_action_permission AS p" in sql:
            return self.permission_rows
        raise AssertionError(f"Unexpected fetch_all query: {sql}")


def test_runtime_uses_registered_objects_and_only_matching_member_grants():
    runtime = UIRuntimeRepository(FakeDatabase())

    snapshot = runtime.load_for_member("member-1")

    assert set(snapshot.object_definitions) == {
        "SP_UI_SCREEN",
        "SP_UI_MENU",
        "SP_UI_ACTION",
        "SP_UI_PERMISSION",
    }
    assert len(snapshot.menus) == 1
    menu = snapshot.menus[0]
    assert menu.screen_id == "SCREEN_REPORT"
    assert menu.menu_code == "MENU_REPORT"
    assert [action.button_code for action in menu.actions] == ["REPORT_READ"]


def test_rule_grants_are_not_guessed_as_member_grants():
    database = FakeDatabase()
    database.permission_rows = [
        {
            "button_code": "REPORT_READ",
            "permission_subject_type_code": "RULE",
            "permission_subject_id": "RULE_REPORT_VIEW",
            "permission_type_code": "READ",
        }
    ]

    snapshot = UIRuntimeRepository(database).load_for_member("member-1")

    assert snapshot.menus == ()
    assert snapshot.unresolved_rule_permission_count == 1


def test_missing_or_inactive_member_is_denied():
    with pytest.raises(PermissionError, match="활성 cm_member"):
        UIRuntimeRepository(FakeDatabase(member_exists=False)).load_for_member("member-1")


def test_missing_ui_screen_identifier_column_fails_closed():
    with pytest.raises(UIRuntimeConfigurationError, match="ui_menu.ui_screen_id"):
        UIRuntimeRepository(
            FakeDatabase(screen_id_column=False)
        ).load_for_member("member-1")


def test_missing_ui_object_definition_fails_closed():
    database = FakeDatabase()
    database.object_rows = database.object_rows[:-1]

    with pytest.raises(UIRuntimeConfigurationError, match="UI Runtime Object 미등록"):
        UIRuntimeRepository(database).load_for_member("member-1")


def test_missing_member_identity_is_denied_before_repository_access():
    with pytest.raises(PermissionError, match="Member ID"):
        UIRuntimeRepository(FakeDatabase()).load_for_member(" ")

class FakeActionDispatcher:
    """Record action dispatches and expose a Repository-shaped Query contract."""

    def __init__(self, required_parameters=(), *, failure=None):
        self.required_parameters = list(required_parameters)
        self.failure = failure
        self.calls = []
        self.metadata_repository = self

    def get_verified_query(self, query_id):
        # The fixture mirrors raw SQL Query records used by the live ui_menu_action rows.
        placeholders = " ".join(f":{name}" for name in self.required_parameters)
        return {
            "query_id": query_id,
            "crud_type": "READ",
            "sql_text": f"SELECT 1 {placeholders}".strip(),
        }

    def dispatch(self, query_id, parameters):
        if self.failure:
            raise self.failure
        self.calls.append((query_id, parameters))
        return {"ok": True}


def test_authorized_action_rechecks_permission_and_dispatches_verified_query():
    # The test proves an active Member grant reaches only the selected Verified Query.
    dispatcher = FakeActionDispatcher()
    runtime = UIRuntimeRepository(FakeDatabase(), action_dispatcher=dispatcher)

    result = runtime.execute_action_for_member("member-1", "REPORT_READ")

    assert result == {"ok": True}
    assert dispatcher.calls == [("QUERY_REPORT_READ", [])]


def test_unauthorized_action_is_rejected_before_query_dispatch():
    # A button outside the fresh permission snapshot must never reach the dispatcher.
    dispatcher = FakeActionDispatcher()
    runtime = UIRuntimeRepository(FakeDatabase(), action_dispatcher=dispatcher)

    with pytest.raises(PermissionError, match="허용된 UI Action"):
        runtime.execute_action_for_member("member-1", "REPORT_UPDATE")

    assert dispatcher.calls == []


def test_parameterized_action_fails_closed_until_form_runtime_exists():
    # The desktop runtime has no parameter form, so required-input procedures stay unexecuted.
    dispatcher = FakeActionDispatcher(required_parameters=("report_id",))
    runtime = UIRuntimeRepository(FakeDatabase(), action_dispatcher=dispatcher)

    with pytest.raises(UIRuntimeConfigurationError, match="필수 SQL 파라미터"):
        runtime.execute_action_for_member("member-1", "REPORT_READ")

    assert dispatcher.calls == []


def test_verified_query_execution_error_propagates_to_ui_error_handler():
    # Dispatcher failures must remain visible to the caller instead of being swallowed.
    dispatcher = FakeActionDispatcher(failure=RuntimeError("repository unavailable"))
    runtime = UIRuntimeRepository(FakeDatabase(), action_dispatcher=dispatcher)

    with pytest.raises(RuntimeError, match="repository unavailable"):
        runtime.execute_action_for_member("member-1", "REPORT_READ")

def test_spds_entrypoint_imports_the_package_ui_module():
    # This regression check catches the former top-level ui.main_window import failure.
    import importlib

    entrypoint = importlib.import_module("spds.app.main")

    assert entrypoint.MainWindow.__module__ == "spds.ui.main_window"

def test_rule_grant_is_applied_through_active_member_role_rule_contract():
    # Only a Rule linked to this Member through the documented Role tables grants access.
    database = FakeDatabase()
    database.permission_rows = [
        {
            "button_code": "REPORT_READ",
            "permission_subject_type_code": "RULE",
            "permission_subject_id": "RULE_REPORT_VIEW",
            "permission_type_code": "READ",
        }
    ]
    database.member_rule_rows = [{"rule_id": "RULE_REPORT_VIEW"}]

    snapshot = UIRuntimeRepository(database).load_for_member("member-1")

    assert [action.button_code for action in snapshot.menus[0].actions] == ["REPORT_READ"]
    assert snapshot.unresolved_rule_permission_count == 0


def test_rule_grant_requires_registered_rule_subject_code():
    # An incomplete subject-type contract must stop rather than silently changing authorization.
    database = FakeDatabase()
    database.code_rows = [
        row for row in database.code_rows
        if not (
            row["group_code"] == "UI_PERMISSION_SUBJECT_TYPE"
            and row["code"] == "RULE"
        )
    ]
    database.permission_rows = [
        {
            "button_code": "REPORT_READ",
            "permission_subject_type_code": "RULE",
            "permission_subject_id": "RULE_REPORT_VIEW",
            "permission_type_code": "READ",
        }
    ]

    with pytest.raises(UIRuntimeConfigurationError, match="RULE 공통코드"):
        UIRuntimeRepository(database).load_for_member("member-1")

def test_verified_query_crud_mismatch_is_rejected_before_dispatch():
    # A READ button must not invoke an active Query registered as DELETE or UPDATE.
    dispatcher = FakeActionDispatcher()
    dispatcher.get_verified_query = lambda query_id: {
        "query_id": query_id,
        "crud_type": "DELETE",
        "sql_text": "DELETE FROM health_report WHERE health_report_id = %s",
    }
    runtime = UIRuntimeRepository(FakeDatabase(), action_dispatcher=dispatcher)

    with pytest.raises(UIRuntimeConfigurationError, match="유형과 Verified SQL CRUD"):
        runtime.execute_action_for_member("member-1", "REPORT_READ")

    assert dispatcher.calls == []
