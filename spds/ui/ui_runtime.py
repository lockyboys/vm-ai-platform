"""Repository-backed UI menu, screen and member-permission runtime."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from common.common_function import logger


class UIRuntimeConfigurationError(RuntimeError):
    """UI Object, schema, or common-code configuration is incomplete."""


class UIVerifiedSqlDispatcher:
    """Bridge UI actions to the existing active, certified Verified SQL execution path."""

    def __init__(self, database) -> None:
        self.database = database

    def get_verified_query(self, query_id: str) -> dict[str, Any]:
        # Reuse the Harness contract loader so certification and Mongo payload checks stay centralized.
        from harness.mcp.tools.verified_sql_tools import _load_executable_query

        return _load_executable_query(self.database, query_id)

    def dispatch(self, query_id: str, parameters: list[Any]) -> Any:
        # All data-changing execution remains inside the reviewed Verified SQL tool path.
        from harness.mcp.tools.verified_sql_tools import verified_sql_execute

        return verified_sql_execute(
            query_id=query_id,
            parameters_json=json.dumps(parameters, ensure_ascii=False),
            apply=True,
        )


@dataclass(frozen=True)
class UIRuntimeAction:
    """One registered action visible to the authenticated member."""

    button_code: str
    button_name: str
    action_type_code: str
    query_id: str
    permission_type_code: str


@dataclass(frozen=True)
class UIRuntimeMenu:
    """One UI Screen/Menu Object with only authorized actions."""

    screen_id: str
    menu_code: str
    menu_name: str
    menu_url: str | None
    screen_type_code: str
    menu_type_code: str
    actions: tuple[UIRuntimeAction, ...]


@dataclass(frozen=True)
class UIRuntimeSnapshot:
    """Read-only runtime snapshot derived from active Repository records."""

    member_id: str
    object_definitions: dict[str, dict[str, Any]]
    menus: tuple[UIRuntimeMenu, ...]
    unresolved_rule_permission_count: int


class UIRuntimeRepository:
    """Load UI Object and permission data from the COMMON Repository.

    The access token must already be verified by CommonAuth. This class
    additionally requires an active cm_member row and applies only explicit
    MEMBER grants. It intentionally does not infer Rule membership.
    """

    _OBJECT_GROUP = "UI_RUNTIME_OBJECT_DEFINITION"
    _OBJECT_CODES = ("SP_UI_SCREEN", "SP_UI_MENU", "SP_UI_ACTION", "SP_UI_PERMISSION")
    _CODE_GROUPS = (
        "UI_SCREEN_TYPE",
        "UI_MENU_TYPE",
        "UI_ACTION_TYPE",
        "UI_PERMISSION_TYPE",
        "UI_PERMISSION_SUBJECT_TYPE",
    )

    def __init__(self, database=None, action_dispatcher=None) -> None:
        # Tests inject fakes; production uses the shared COMMON Repository and its verified-query runtime.
        if database is None:
            from common.database import CommonDatabase

            database = CommonDatabase(database_role="COMMON")
        self.database = database
        self.action_dispatcher = action_dispatcher or UIVerifiedSqlDispatcher(database)

    def execute_action_for_member(
        self, member_id: str, button_code: str, parameters: list[Any] | None = None
    ) -> Any:
        """Recheck live grants, then dispatch only an active Verified Query contract."""
        if self.action_dispatcher is None:
            raise UIRuntimeConfigurationError("Verified SQL 실행기가 구성되지 않았습니다.")

        # Reload Repository permissions at click time so revoked grants do not remain usable.
        snapshot = self.load_for_member(member_id)
        action = next(
            (
                candidate
                for menu in snapshot.menus
                for candidate in menu.actions
                if candidate.button_code == button_code
            ),
            None,
        )
        if action is None:
            raise PermissionError("현재 Member에게 허용된 UI Action이 아닙니다.")

        # Verify the menu action's CRUD contract against the active, certified Query before execution.
        query = self.action_dispatcher.get_verified_query(action.query_id)
        if str(query.get("crud_type") or "").upper() != action.action_type_code:
            raise UIRuntimeConfigurationError(
                "UI Action 유형과 Verified SQL CRUD 유형이 일치하지 않습니다."
            )

        # SQL parameter types/forms are not registered yet; never guess values or their order.
        sql_text = str(query.get("sql_text") or "")
        required_names = re.findall(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)", sql_text)
        supplied_parameters = parameters or []
        if required_names:
            raise UIRuntimeConfigurationError(
                "필수 SQL 파라미터 입력 화면이 없어 UI Action 실행을 중단했습니다."
            )
        if not isinstance(supplied_parameters, list) or supplied_parameters:
            raise UIRuntimeConfigurationError(
                "UI Action 파라미터는 검증된 입력 화면이 연결되어야 전달할 수 있습니다."
            )
        return self.action_dispatcher.dispatch(action.query_id, supplied_parameters)

    def load_for_member(self, member_id: str) -> UIRuntimeSnapshot:
        normalized_member_id = str(member_id or "").strip()
        if not normalized_member_id:
            raise PermissionError("로그인된 Member ID가 필요합니다.")

        object_definitions = self._load_object_definitions()
        code_sets = self._load_code_sets()
        self._require_screen_identifier_column()

        member = self.database.fetch_one(
            """
            SELECT member_id
            FROM cm_member
            WHERE member_id = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            """,
            (normalized_member_id,),
        )
        if not member:
            raise PermissionError("활성 cm_member를 확인하지 못해 UI 접근을 거부했습니다.")

        menus = self.database.fetch_all(
            """
            SELECT
                m.menu_code,
                m.ui_screen_id,
                m.menu_name,
                m.menu_url,
                m.ui_screen_type_code,
                m.ui_menu_type_code,
                m.menu_sort_no
            FROM ui_menu AS m
            WHERE m.status_code = 'ACTIVE'
              AND m.deleted_dt IS NULL
            ORDER BY m.menu_sort_no, m.menu_code
            """
        )
        actions = self.database.fetch_all(
            """
            SELECT
                a.button_code,
                a.menu_code,
                a.button_name,
                a.ui_action_type_code,
                a.query_id,
                a.button_sort_no
            FROM ui_menu_action AS a
            WHERE a.status_code = 'ACTIVE'
              AND a.deleted_dt IS NULL
            ORDER BY a.menu_code, a.button_sort_no, a.button_code
            """
        )
        permissions = self.database.fetch_all(
            """
            SELECT
                p.button_code,
                p.permission_subject_type_code,
                p.permission_subject_id,
                p.permission_type_code
            FROM ui_menu_action_permission AS p
            WHERE p.status_code = 'ACTIVE'
              AND p.deleted_dt IS NULL
            """
        )

        subject_types = code_sets["UI_PERMISSION_SUBJECT_TYPE"]
        if "MEMBER" not in subject_types:
            raise UIRuntimeConfigurationError(
                "UI_PERMISSION_SUBJECT_TYPE의 MEMBER 공통코드가 비활성 또는 미등록입니다."
            )

        member_grants: set[tuple[str, str]] = set()
        unresolved_rule_permission_count = 0
        permission_types = code_sets["UI_PERMISSION_TYPE"]
        has_rule_permissions = any(
            permission.get("permission_subject_type_code") == "RULE"
            for permission in permissions
        )
        if has_rule_permissions and "RULE" not in subject_types:
            raise UIRuntimeConfigurationError(
                "UI_PERMISSION_SUBJECT_TYPE의 RULE 공통코드가 비활성 또는 미등록입니다."
            )

        # Resolve Member -> Role -> Rule only through the live Repository relations.
        member_rule_ids = set()
        if has_rule_permissions:
            rule_rows = self.database.fetch_all(
                """
                /* Purpose: Resolve active Member-to-Rule grants through documented Role relations. */
                SELECT DISTINCT rule.rule_id
                FROM cm_member_role AS member_role
                JOIN cm_role AS role
                  ON role.role_id = member_role.role_id
                JOIN cm_role_rule AS role_rule
                  ON role_rule.role_id = role.role_id
                JOIN rl_rule AS rule
                  ON rule.rule_id = role_rule.rule_id
                WHERE member_role.member_id = %s
                  AND member_role.status_code = 'ACTIVE'
                  AND member_role.deleted_dt IS NULL
                  AND role.status_code = 'ACTIVE'
                  AND role.deleted_dt IS NULL
                  AND role_rule.deleted_dt IS NULL
                  AND rule.status_code = 'ACTIVE'
                  AND rule.deleted_dt IS NULL
                """,
                (normalized_member_id,),
            )
            member_rule_ids = {
                str(row["rule_id"]) for row in rule_rows if row.get("rule_id")
            }

        for permission in permissions:
            subject_type = permission.get("permission_subject_type_code")
            permission_type = permission.get("permission_type_code")
            if subject_type == "RULE":
                if (
                    permission.get("permission_subject_id") in member_rule_ids
                    and permission_type in permission_types
                ):
                    member_grants.add((permission.get("button_code"), permission_type))
                else:
                    # Keep unmatched/inactive Rule assignments observable without granting access.
                    unresolved_rule_permission_count += 1
                continue
            if (
                subject_type == "MEMBER"
                and permission.get("permission_subject_id") == normalized_member_id
                and permission_type in permission_types
            ):
                member_grants.add((permission.get("button_code"), permission_type))

        actions_by_menu: dict[str, list[UIRuntimeAction]] = {}
        action_types = code_sets["UI_ACTION_TYPE"]
        for row in actions:
            action_type = row.get("ui_action_type_code")
            if action_type not in action_types:
                raise UIRuntimeConfigurationError(
                    f"등록되지 않은 UI_ACTION_TYPE: {action_type!r}"
                )
            # Exact type matching avoids broadening CREATE/UPDATE/DELETE grants.
            if (row.get("button_code"), action_type) not in member_grants:
                continue
            action = UIRuntimeAction(
                button_code=str(row["button_code"]),
                button_name=str(row["button_name"]),
                action_type_code=str(action_type),
                query_id=str(row["query_id"]),
                permission_type_code=str(action_type),
            )
            actions_by_menu.setdefault(str(row["menu_code"]), []).append(action)

        menu_types = code_sets["UI_MENU_TYPE"]
        screen_types = code_sets["UI_SCREEN_TYPE"]
        runtime_menus: list[UIRuntimeMenu] = []
        for row in menus:
            menu_type = row.get("ui_menu_type_code")
            screen_type = row.get("ui_screen_type_code") or ""
            if menu_type not in menu_types:
                raise UIRuntimeConfigurationError(
                    f"등록되지 않은 UI_MENU_TYPE: {menu_type!r}"
                )
            if screen_type and screen_type not in screen_types:
                raise UIRuntimeConfigurationError(
                    f"등록되지 않은 UI_SCREEN_TYPE: {screen_type!r}"
                )
            visible_actions = tuple(actions_by_menu.get(str(row["menu_code"]), ()))
            # A menu is visible only when the signed-in member has a direct or resolved Rule grant.
            if not visible_actions:
                continue
            screen_id = str(row.get("ui_screen_id") or "").strip()
            if menu_type == "ITEM" and (not screen_id or not screen_type):
                raise UIRuntimeConfigurationError(
                    f"UI Screen 식별자/유형 누락: menu_code={row.get('menu_code')}"
                )
            runtime_menus.append(
                UIRuntimeMenu(
                    screen_id=screen_id,
                    menu_code=str(row["menu_code"]),
                    menu_name=str(row["menu_name"]),
                    menu_url=row.get("menu_url"),
                    screen_type_code=screen_type,
                    menu_type_code=str(menu_type),
                    actions=visible_actions,
                )
            )

        if unresolved_rule_permission_count:
            logger.warning(
                "UI Runtime: %s Rule grants did not match an active Member-Role-Rule relation.",
                unresolved_rule_permission_count,
            )
        return UIRuntimeSnapshot(
            member_id=normalized_member_id,
            object_definitions=object_definitions,
            menus=tuple(runtime_menus),
            unresolved_rule_permission_count=unresolved_rule_permission_count,
        )

    def _load_object_definitions(self) -> dict[str, dict[str, Any]]:
        placeholders = ", ".join(["%s"] * len(self._OBJECT_CODES))
        rows = self.database.fetch_all(
            f"""
            SELECT code, common_code_json
            FROM cm_common_code
            WHERE group_code = %s
              AND code IN ({placeholders})
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            """,
            (self._OBJECT_GROUP, *self._OBJECT_CODES),
        )
        definitions: dict[str, dict[str, Any]] = {}
        for row in rows:
            raw = row.get("common_code_json")
            try:
                value = json.loads(raw) if isinstance(raw, str) else raw
            except (TypeError, json.JSONDecodeError) as exc:
                raise UIRuntimeConfigurationError(
                    f"UI Object 정의 JSON이 잘못되었습니다: {row.get('code')}"
                ) from exc
            if not isinstance(value, dict):
                raise UIRuntimeConfigurationError(
                    f"UI Object 정의가 객체가 아닙니다: {row.get('code')}"
                )
            definitions[str(row["code"])] = value

        missing = set(self._OBJECT_CODES) - definitions.keys()
        if missing:
            raise UIRuntimeConfigurationError(
                f"UI Runtime Object 미등록: {', '.join(sorted(missing))}"
            )
        screen_definition = definitions["SP_UI_SCREEN"]
        if (
            screen_definition.get("target_identifier_field") != "ui_screen_id"
            or screen_definition.get("object_level") != 3
        ):
            raise UIRuntimeConfigurationError(
                "SP_UI_SCREEN 정의가 ui_screen_id / Level 3 계약과 다릅니다."
            )
        return definitions

    def _load_code_sets(self) -> dict[str, set[str]]:
        placeholders = ", ".join(["%s"] * len(self._CODE_GROUPS))
        rows = self.database.fetch_all(
            f"""
            SELECT group_code, code
            FROM cm_common_code
            WHERE group_code IN ({placeholders})
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            """,
            self._CODE_GROUPS,
        )
        result = {group: set() for group in self._CODE_GROUPS}
        for row in rows:
            result.setdefault(str(row["group_code"]), set()).add(str(row["code"]))
        missing = [group for group, codes in result.items() if not codes]
        if missing:
            raise UIRuntimeConfigurationError(
                f"UI 공통코드 Group이 비어 있습니다: {', '.join(missing)}"
            )
        return result

    def _require_screen_identifier_column(self) -> None:
        # The UI Screen Object contract requires this migration; never substitute menu_code.
        column = self.database.fetch_one(
            """
            SELECT COUNT(*) AS column_count
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'ui_menu'
              AND column_name = 'ui_screen_id'
            """
        )
        if not column or int(column.get("column_count") or 0) != 1:
            raise UIRuntimeConfigurationError(
                "ui_menu.ui_screen_id가 없습니다. "
                "sql/ui_runtime/11_migrate_ui_screen_identifier_20260803.sql 적용 후 재시도하세요."
            )
