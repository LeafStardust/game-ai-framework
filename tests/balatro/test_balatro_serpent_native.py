from types import SimpleNamespace

import games.balatro  # noqa: F401 - initialize production registration
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.serpent_draw_policy import SERPENT_DRAW_COUNT, serpent_draw_count


def _state(*, boss_name="The Serpent", hand_size=8):
    return SimpleNamespace(
        boss_name=boss_name,
        hand_size=hand_size,
        jokers=[],
    )


def test_base_planner_owns_serpent_post_action_draw_count():
    state = _state()

    assert LiveBlindClearPlanner._post_action_draw_count(state, 1) == SERPENT_DRAW_COUNT
    assert LiveBlindClearPlanner._post_action_draw_count(state, 5) == SERPENT_DRAW_COUNT


def test_base_planner_preserves_ordinary_draw_count_without_serpent():
    state = _state(boss_name="The Hook")

    assert LiveBlindClearPlanner._post_action_draw_count(state, 2) == 2
    assert LiveBlindClearPlanner._post_action_draw_count(state, -1) == 0


def test_compatibility_helper_matches_native_serpent_rule():
    state = _state()

    assert serpent_draw_count(state, 1) == SERPENT_DRAW_COUNT
    assert serpent_draw_count(state, 5) == SERPENT_DRAW_COUNT


def test_integrated_d1_still_owns_serpent_draw_count_natively():
    state = _state(hand_size=8)
    retained_cards = [object(), object(), object(), object(), object(), object()]

    assert D1LiveBlindClearPlanner()._post_action_draw_count(state, retained_cards) == (
        SERPENT_DRAW_COUNT
    )


def test_production_stack_does_not_install_serpent_overlay():
    assert not hasattr(LiveBlindClearPlanner, "_serpent_draw_policy_installed")
