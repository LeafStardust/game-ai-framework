from games.balatro.live.injected.consumable_target_postcondition import (
    build_consumable_target_postcondition_for_consumable,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.spectrals import BlackHole
from games.balatro.state import BalatroState


def _snapshot(levels: dict[str, int]) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=2,
        phase="SPECTRAL_PACK",
        state_complete=True,
        payload={
            "hands": {
                hand_type: {"level": level}
                for hand_type, level in levels.items()
            }
        },
    )


def test_black_hole_requires_every_modeled_hand_level_to_increase_by_one():
    state = BalatroState()
    state.hand_levels = {
        "HIGH_CARD": 1,
        "PAIR": 2,
        "FLUSH": 4,
    }

    postcondition = build_consumable_target_postcondition_for_consumable(
        state,
        consumable=BlackHole(),
        target_indices=(),
    )

    assert postcondition is not None
    assert postcondition.expected_hand_levels == (
        ("FLUSH", 5),
        ("HIGH_CARD", 2),
        ("PAIR", 3),
    )
    assert postcondition.matches(
        _snapshot(
            {
                "HIGH_CARD": 2,
                "PAIR": 3,
                "FLUSH": 5,
            }
        )
    )


def test_black_hole_rejects_partial_hand_level_transition():
    state = BalatroState()
    state.hand_levels = {
        "HIGH_CARD": 1,
        "PAIR": 2,
        "FLUSH": 4,
    }

    postcondition = build_consumable_target_postcondition_for_consumable(
        state,
        consumable=BlackHole(),
        target_indices=(),
    )

    assert postcondition is not None
    assert not postcondition.matches(
        _snapshot(
            {
                "HIGH_CARD": 2,
                "PAIR": 2,
                "FLUSH": 5,
            }
        )
    )
