import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.amber_acorn import disable_amber_acorn
from games.balatro.env.blind_start import prepare_supported_amber_acorn_start
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.state import BalatroState


def _started() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.round = 4
    state.ante = 3
    state.boss_name = "Amber Acorn"
    state.blind = Blind(BlindType.BOSS, 4000)
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.jokers = []
    for live_id, joker_type in enumerate(
        (FlatMultJoker, JollyJoker, SlyJoker),
        start=21,
    ):
        joker = joker_type()
        joker.live_id = live_id
        state.jokers.append(joker)
    return prepare_supported_amber_acorn_start(
        HeadlessRunState(public=state, seed="AMBER-CLEANUP")
    )


def _ids(state):
    return [getattr(joker, "live_id", None) for joker in state.jokers]


def test_env_r2_amber_disable_reveals_retained_physical_order_without_restoring_creation_order():
    run = _started()
    physical = _ids(run.public)
    creation = [joker.live_id for joker in run.require_joker_order_state().creation_order]
    assert physical != creation
    assert all(
        getattr(joker, "live_id", None) is None
        for joker in public_observation_state(run.public).jokers
    )
    before_rng = run.rng_snapshot()

    disabled = disable_amber_acorn(run)
    observation = public_observation_state(disabled.public)

    assert disabled.public.blind.disabled is True
    assert run.public.blind.disabled is False
    assert _ids(disabled.public) == physical
    assert _ids(observation) == physical
    assert disabled.rng_snapshot() == before_rng
    assert [joker.live_id for joker in disabled.require_joker_order_state().physical_order] == physical


def test_env_r2_amber_leaving_hidden_hand_phases_reveals_same_physical_order_after_defeat_boundary():
    run = _started()
    physical = _ids(run.public)

    after_defeat = run.copy()
    after_defeat.public.phase = "SHOP"
    observation = public_observation_state(after_defeat.public)

    assert _ids(observation) == physical
    assert _ids(after_defeat.public) == physical


def test_env_r2_amber_disable_rejects_wrong_missing_or_already_disabled_blind():
    run = _started()
    wrong = run.copy()
    wrong.public.boss_name = "Verdant Leaf"
    with pytest.raises(HeadlessTransitionError, match="requires Amber Acorn"):
        disable_amber_acorn(wrong)

    missing = run.copy()
    missing.public.blind = None
    with pytest.raises(HeadlessTransitionError, match="authoritative blind state"):
        disable_amber_acorn(missing)

    disabled = disable_amber_acorn(run)
    with pytest.raises(HeadlessTransitionError, match="already disabled"):
        disable_amber_acorn(disabled)
