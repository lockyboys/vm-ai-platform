import pytest

from src.common.navigation import (
    NavigationNode,
    NavigationNodeType,
)


def test_navigation_node_add_child() -> None:
    root = NavigationNode(
        key="repository",
        label="Repository",
        node_type=NavigationNodeType.ROOT,
    )

    child = root.add_child(
        NavigationNode(
            key="te_story_platform",
            label="te_story_platform",
            node_type=NavigationNodeType.GROUP,
        )
    )

    assert root.find_child("te_story_platform") is child
    assert root.is_leaf is False
    assert child.is_leaf is True


def test_navigation_node_walk() -> None:
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

    database.add_child(
        NavigationNode(
            key="cm_common_code",
            label="cm_common_code",
            node_type=NavigationNodeType.ITEM,
        )
    )

    assert [
        node.key
        for node in root.walk()
    ] == [
        "repository",
        "te_story_platform",
        "cm_common_code",
    ]


def test_navigation_node_rejects_duplicate_child_key() -> None:
    root = NavigationNode(
        key="repository",
        label="Repository",
    )

    root.add_child(
        NavigationNode(
            key="table",
            label="Table",
        )
    )

    with pytest.raises(
        ValueError,
        match="duplicate child key: table",
    ):
        root.add_child(
            NavigationNode(
                key="table",
                label="Duplicate Table",
            )
        )
