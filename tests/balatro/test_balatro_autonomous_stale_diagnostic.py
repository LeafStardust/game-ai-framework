from games.balatro.live.external.live_memory_autonomous_stale_diagnostic import (
    semantic_differences,
)


def test_semantic_differences_reports_leaf_paths():
    before = {
        "money": 5,
        "hand": {"cards": [{"live_id": 1, "debuff": False}]},
    }
    after = {
        "money": 6,
        "hand": {"cards": [{"live_id": 1, "debuff": True}]},
    }

    differences = semantic_differences(before, after)

    assert [(item.path, item.before, item.after) for item in differences] == [
        ("payload.hand.cards[0].debuff", False, True),
        ("payload.money", 5, 6),
    ]


def test_semantic_differences_is_bounded():
    before = {f"field_{index}": 0 for index in range(10)}
    after = {f"field_{index}": 1 for index in range(10)}

    differences = semantic_differences(before, after, limit=3)

    assert len(differences) == 3
