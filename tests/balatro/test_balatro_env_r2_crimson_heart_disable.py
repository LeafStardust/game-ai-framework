import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.crimson_heart import (
    apply_crimson_heart_drawn_to_hand,
    disable_crimson_heart,
    set_crimson_heart_prepped,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.state import BalatroState


def _targeted_run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SELECTING_HAND"
    state.boss_name = "Crimson Heart"
    state.blind = Blind(BlindType.BOSS, 1000)
    for index in range(3):
        joker = FlatMultJoker(index + 1)
        joker.live_id = 500 + index
        state.jokers.append(joker)
    run = HeadlessRunState(public=state, seed="CRIMSONDISABLE")
    run = set_crimson_heart_prepped(run, True)
    return apply_crimson_heart_drawn_to_hand(run)


def test_env_r2_crimson_disable_clears_joker_debuff_and_prepped_without_rng():
    run = _targeted_run()
    assert sum(bool(getattr(joker, "debuffed", False)) for joker in run.public.jokers) == 1
    setattr(run.public.blind, "prepped", True)
    before = run.rng_snapshot()

    result = disable_crimson_heart(run)

    assert result.public.blind.disabled is True
    assert getattr(result.public.blind, "prepped") is False
    assert all(not bool(getattr(joker, "debuffed", False)) for joker in result.public.jokers)
    assert result.rng_snapshot() == before
    assert run.public.blind.disabled is False
    assert sum(bool(getattr(joker, "debuffed", False)) for joker in run.public.jokers) == 1


def test_env_r2_crimson_disable_rejects_already_disabled_blind():
    run = _targeted_run()
    run.public.blind.disabled = True

    with pytest.raises(HeadlessTransitionError, match="already disabled"):
        disable_crimson_heart(run)
