from src.common.navigation import (
    NavigationModel,
    NavigationNode,
    NavigationNodeType,
)
from src.common.navigation.navigator import Navigator


def create_model() -> NavigationModel:
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

    return NavigationModel(root)


def test_navigator_default_root():
    nav = Navigator(create_model())

    assert nav.current.key == "repository"


def test_navigator_goto():
    nav = Navigator(create_model())

    nav.goto("cm_common_code")

    assert nav.current.key == "cm_common_code"


def test_navigator_reset():
    nav = Navigator(create_model())

    nav.goto("cm_common_code")
    nav.reset()

    assert nav.current.key == "repository"


def test_navigator_path():
    nav = Navigator(create_model())

    nav.goto("cm_common_code")

    assert nav.path() == [
        "repository",
        "te_story_platform",
        "cm_common_code",
    ]
