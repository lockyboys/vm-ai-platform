from src.common.navigation import (
    NavigationModel,
    NavigationNode,
    NavigationNodeType,
)

from src.common.navigation.renderer import TreeRenderer


def test_tree_renderer():

    root = NavigationNode(
        key="repository",
        label="Repository",
        node_type=NavigationNodeType.ROOT,
    )

    db = root.add_child(
        NavigationNode(
            key="te_story_platform",
            label="te_story_platform",
            node_type=NavigationNodeType.GROUP,
        )
    )

    db.add_child(
        NavigationNode(
            key="cm_common_code",
            label="cm_common_code",
        )
    )

    model = NavigationModel(root)

    output = TreeRenderer().render(model)

    assert "Repository" in output
    assert "te_story_platform" in output
    assert "cm_common_code" in output
