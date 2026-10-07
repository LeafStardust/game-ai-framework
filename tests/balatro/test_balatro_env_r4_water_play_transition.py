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


def _water_run(*, requirement=1):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 2
    state.round = 5
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=5)
    state.boss_name = "The Water"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_resource_boss(
        HeadlessRunState(public=state, seed="R4-WATER")
    )


def test_env_r4_water_plays_with_zero_discards_and_clears_stored_state_on_defeat():
    run = _water_run()
    snapshot = serialize_headless_run_state(run)
    restored = restore_headless_run_state(snapshot)
    before_rng = restored.rng_snapshot()

    result = apply_supported_ordinary_play(restored, (0,))
    defeated = defeat_supported_boss(result)

    assert restored.public.discards_remaining == 0
    assert restored.boss_discards_sub == 3
    assert result.public.phase == "ROUND_EVAL"
    assert result.public.discards_remaining == 0
    assert result.boss_discards_sub == 3
    assert result.rng_snapshot() == before_rng
    assert defeated.boss_discards_sub is None
    assert serialize_headless_run_state(run) == snapshot


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("boss_discards_sub", None),
        ("boss_discards_sub", True),
        ("boss_discards_sub", -1),
        ("boss_hands_sub", 1),
        ("boss_hand_size_sub", 1),
    ],
)
def test_env_r4_water_rejects_inexact_private_resource_state_atomically(field, value):
    run = _water_run(requirement=99_999)
    setattr(run, field, value)
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="Water action"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("discards_remaining", 1),
        ("discards_remaining", False),
        ("round_reset_discards_observed", False),
        ("round_reset_discards", True),
        ("round_reset_discards", -1),
    ],
)
def test_env_r4_water_rejects_inexact_public_resource_state_atomically(field, value):
    run = _water_run(requirement=99_999)
    setattr(run.public, field, value)
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="Water action"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
