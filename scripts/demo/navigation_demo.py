from src.common.navigation import (
    NavigationModel,
    NavigationNode,
    NavigationNodeType,
)
from src.common.navigation.renderer import TreeRenderer


def build_demo_model() -> NavigationModel:
    root = NavigationNode(
        key="repository",
        label="Repository",
        node_type=NavigationNodeType.ROOT,
    )

    database = root.add_child(
        NavigationNode(
            key="te_story_platform",
            label="te_story_platform",
            node_type=NavigationNodeType.GROUP,
        )
    )

    table = database.add_child(
        NavigationNode(
            key="cm_common_code",
            label="cm_common_code",
            node_type=NavigationNodeType.ITEM,
        )
    )

    table.add_child(
        NavigationNode(
            key="group_code",
            label="group_code",
            node_type=NavigationNodeType.VALUE,
        )
    )

    table.add_child(
        NavigationNode(
            key="code",
            label="code",
            node_type=NavigationNodeType.VALUE,
        )
    )

    table.add_child(
        NavigationNode(
            key="code_name",
            label="code_name",
            node_type=NavigationNodeType.VALUE,
        )
    )

    table.add_child(
        NavigationNode(
            key="status_code",
            label="status_code",
            node_type=NavigationNodeType.VALUE,
        )
    )

    return NavigationModel(root=root)


def main() -> None:
    model = build_demo_model()
    output = TreeRenderer().render(model)

    print()
    print("Navigation Framework Demo")
    print("=" * 40)
    print(output)
    print("=" * 40)
    print()


if __name__ == "__main__":
    main()
