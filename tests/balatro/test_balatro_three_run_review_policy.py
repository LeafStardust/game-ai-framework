from types import SimpleNamespace

from games.balatro.three_run_review_policy import (
    _free_joker_slots,
    _has_hand_specialization,
)


def test_review_guard_detects_large_unfilled_joker_board():
    state = SimpleNamespace(joker_slots=5, jokers=[object(), object(), object()])
    assert _free_joker_slots(state) == 2


def test_review_guard_does_not_count_full_board_as_development_deficit():
    state = SimpleNamespace(joker_slots=5, jokers=[object()] * 5)
    assert _free_joker_slots(state) == 0


def test_planet_market_requires_actual_hand_level_specialization():
    unrefined = SimpleNamespace(
        hands={"Pair": SimpleNamespace(level=1), "Flush": SimpleNamespace(level=1)}
    )
    refined = SimpleNamespace(
        hands={"Pair": SimpleNamespace(level=1), "Flush": SimpleNamespace(level=2)}
    )

    assert not _has_hand_specialization(unrefined)
    assert _has_hand_specialization(refined)


def test_hand_specialization_supports_snapshot_dict_shape():
    state = SimpleNamespace(hands={"Pair": {"level": 3}})
    assert _has_hand_specialization(state)
