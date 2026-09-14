import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_resource_boss
from games.balatro.env.boss_defeat import defeat_supported_boss
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.serialization import (
    restore_headless_run_state,
    serialize_headless_run_state,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _needle_run(*, requirement=1):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 7
    state.round = 17
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=5)
    state.boss_name = "The Needle"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_resource_boss(
        HeadlessRunState(public=state, seed="R4-NEEDLE")
    )


def test_env_r4_needle_restores_stored_one_hand_round_and_clears_on_defeat():
    run = _needle_run()
    snapshot = serialize_headless_run_state(run)
    restored = restore_headless_run_state(snapshot)

    result = apply_supported_ordinary_play(restored, (0,))
    defeated = defeat_supported_boss(result)

    assert restored.public.hands_remaining == 1
    assert restored.boss_hands_sub == 3
    assert result.public.phase == "ROUND_EVAL"
    assert result.public.hands_remaining == 0
    assert result.boss_hands_sub == 3
    assert defeated.boss_hands_sub is None
    assert serialize_headless_run_state(run) == snapshot


@pytest.mark.parametrize(
    "field, value",
    [
        ("boss_hands_sub", None),
        ("boss_hands_sub", 2),
        ("boss_discards_sub", 1),
        ("boss_hand_size_sub", 1),
    ],
)
def test_env_r4_needle_rejects_inexact_resource_state_atomically(field, value):
    run = _needle_run(requirement=99_999)
    setattr(run, field, value)
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="Needle Play"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before


def test_env_r4_needle_rejects_unobserved_reset_hands_atomically():
    run = _needle_run(requirement=99_999)
    run.public.round_reset_hands_observed = False
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="Needle Play"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
