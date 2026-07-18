import pytest

from src.common.navigation import (
    NavigationModel,
    NavigationNode,
    NavigationNodeType,
)


def create_navigation_model() -> NavigationModel:
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

    return NavigationModel(root=root)


def test_navigation_model_find() -> None:
    model = create_navigation_model()

    node = model.find("cm_common_code")

    assert node is not None
    assert node.label == "cm_common_code"


def test_navigation_model_add() -> None:
    model = create_navigation_model()

    column = model.add(
        parent_key="cm_common_code",
        child=NavigationNode(
            key="group_code",
            label="group_code",
            node_type=NavigationNodeType.VALUE,
        ),
    )

    assert column is model.find("group_code")
    assert model.count() == 4


def test_navigation_model_contains() -> None:
    model = create_navigation_model()

    assert model.contains("te_story_platform") is True
    assert model.contains("unknown") is False


def test_navigation_model_require_raises_key_error() -> None:
    model = create_navigation_model()

    with pytest.raises(
        KeyError,
        match="navigation node not found: unknown",
    ):
        model.require("unknown")


def test_navigation_model_walk_order() -> None:
    model = create_navigation_model()

    assert [
        node.key
        for node in model.walk()
    ] == [
        "repository",
        "te_story_platform",
        "cm_common_code",
    ]
