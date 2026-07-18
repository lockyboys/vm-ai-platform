"""Story Programming Repository Explorer 화면 출력 데모."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Static, Tree
from textual.widgets.tree import TreeNode


class RepositoryExplorerApp(App[None]):
    """Repository Navigation Framework의 첫 번째 터미널 화면."""

    TITLE = "Story Programming Repository Explorer"
    SUB_TITLE = "Navigation Framework Demo"

    CSS = """
    Screen {
        layout: vertical;
    }

    #workspace {
        height: 1fr;
    }

    #repository_tree {
        width: 45%;
        border: round $accent;
        padding: 0 1;
    }

    #information_panel {
        width: 55%;
        border: round $accent;
        padding: 1 2;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """화면 구성 요소를 생성한다."""
        yield Header()

        with Horizontal(id="workspace"):
            yield Tree("Repository", id="repository_tree")
            yield Static(
                self._build_information(
                    object_name="Repository",
                    object_type="ROOT",
                    description="Story Programming Repository 탐색 시작점",
                ),
                id="information_panel",
            )

        yield Footer()

    def on_mount(self) -> None:
        """Repository Tree 샘플 구조를 생성한다."""
        tree = self.query_one("#repository_tree", Tree)
        root = tree.root
        root.data = {
            "object_name": "Repository",
            "object_type": "ROOT",
            "description": "Story Programming Repository 탐색 시작점",
        }

        database = root.add(
            "te_story_platform",
            data={
                "object_name": "te_story_platform",
                "object_type": "DATABASE",
                "description": "Story Programming Framework Repository Database",
            },
        )

        common = database.add(
            "Common",
            data={
                "object_name": "Common",
                "object_type": "DOMAIN",
                "description": "공통 Repository Object 영역",
            },
        )

        common_code = common.add(
            "cm_common_code",
            data={
                "object_id": "OB_2026_00021",
                "object_name": "cm_common_code",
                "object_type": "TABLE",
                "business": "STORY_PROGRAMMING",
                "domain": "REPOSITORY",
                "description": "공통 코드와 Repository 메타데이터를 관리하는 Table",
            },
        )

        columns = [
            ("group_code", "VARCHAR(99)", "공통 코드 그룹"),
            ("code", "VARCHAR(99)", "공통 코드"),
            ("code_name", "VARCHAR(150)", "공통 코드명"),
            (
                "common_code_description",
                "VARCHAR(2000)",
                "공통 코드 설명",
            ),
            ("common_code_json", "LONGTEXT", "공통 코드 구조화 지식"),
            ("status_code", "VARCHAR(99)", "상태 코드"),
        ]

        for column_name, data_type, description in columns:
            common_code.add_leaf(
                column_name,
                data={
                    "object_name": column_name,
                    "object_type": "COLUMN",
                    "data_type": data_type,
                    "description": description,
                    "parent_object": "cm_common_code",
                },
            )

        story = database.add(
            "Story",
            data={
                "object_name": "Story",
                "object_type": "DOMAIN",
                "description": "Story Object Repository 영역",
            },
        )

        for table_name in (
            "sp_object",
            "sp_attribute",
            "sp_relationship",
            "sp_metadata",
        ):
            story.add_leaf(
                table_name,
                data={
                    "object_name": table_name,
                    "object_type": "TABLE",
                    "description": f"{table_name} Repository Table",
                },
            )

        runtime = database.add(
            "Runtime",
            data={
                "object_name": "Runtime",
                "object_type": "DOMAIN",
                "description": "Object Runtime 실행 영역",
            },
        )

        runtime.add_leaf(
            "sp_execution_history",
            data={
                "object_name": "sp_execution_history",
                "object_type": "TABLE",
                "description": "Runtime 실행 이력 Repository Table",
            },
        )

        root.expand()
        database.expand()
        common.expand()
        common_code.expand()

        tree.focus()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """선택한 Repository Object 정보를 오른쪽에 표시한다."""
        node: TreeNode = event.node
        information = node.data or {}

        panel = self.query_one("#information_panel", Static)
        panel.update(
            self._build_information(
                object_id=information.get("object_id", "-"),
                object_name=information.get("object_name", str(node.label)),
                object_type=information.get("object_type", "-"),
                business=information.get("business", "-"),
                domain=information.get("domain", "-"),
                data_type=information.get("data_type", "-"),
                parent_object=information.get("parent_object", "-"),
                description=information.get("description", "-"),
            )
        )

    @staticmethod
    def _build_information(
        *,
        object_id: str = "-",
        object_name: str = "-",
        object_type: str = "-",
        business: str = "-",
        domain: str = "-",
        data_type: str = "-",
        parent_object: str = "-",
        description: str = "-",
    ) -> str:
        """오른쪽 Object Information 내용을 생성한다."""
        return (
            "[b]Object Information[/b]\n"
            "────────────────────────────────────────\n\n"
            f"[b]Object ID[/b]     : {object_id}\n"
            f"[b]Object Name[/b]   : {object_name}\n"
            f"[b]Object Type[/b]   : {object_type}\n"
            f"[b]Business[/b]      : {business}\n"
            f"[b]Domain[/b]        : {domain}\n"
            f"[b]Data Type[/b]     : {data_type}\n"
            f"[b]Parent Object[/b] : {parent_object}\n\n"
            "[b]Description[/b]\n"
            f"{description}\n\n"
            "[b]Navigation[/b]\n"
            "• Documents\n"
            "• Rules\n"
            "• APIs\n"
            "• Source\n"
            "• Tests\n"
            "• Runtime\n"
            "• Git History"
        )


def main() -> None:
    """Repository Explorer를 실행한다."""
    RepositoryExplorerApp().run()


if __name__ == "__main__":
    main()
