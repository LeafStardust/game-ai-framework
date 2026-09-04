import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import prepare_supported_amber_acorn_start
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.state import BalatroState


def _run(joker_types=(FlatMultJoker, JollyJoker)) -> HeadlessRunState:
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
    for live_id, joker_type in enumerate(joker_types, start=11):
        joker = joker_type()
        joker.live_id = live_id
        state.jokers.append(joker)
    return HeadlessRunState(public=state, seed="AMBER-START")


def test_env_r2_amber_start_orders_shuffle_before_setting_blind_and_masks_public_order():
    run = _run((BurglarJoker, FlatMultJoker, JollyJoker))
    original_order = list(run.public.jokers)

    result = prepare_supported_amber_acorn_start(run)

    assert result.public.round == 5
    assert result.public.blind_score == 4000
    assert result.public.hands_remaining == 7
    assert result.public.discards_remaining == 0
    assert result.public.phase == "DRAW_TO_HAND"
    assert "aajk" in result.rng.nodes
    assert result.require_joker_order_state().physical_order == result.public.jokers
    assert run.public.jokers == original_order
    assert "aajk" not in run.rng.nodes

    observation = public_observation_state(result.public)
    assert [type(joker).__name__ for joker in observation.jokers] == sorted(
        type(joker).__name__ for joker in result.public.jokers
    )
    assert all(getattr(joker, "live_id", None) is None for joker in observation.jokers)


def test_env_r2_amber_start_one_joker_consumes_no_aajk_rng():
    run = _run((FlatMultJoker,))

    result = prepare_supported_amber_acorn_start(run)

    assert "aajk" not in result.rng.nodes
    assert len(result.public.jokers) == 1


def test_env_r2_amber_start_fails_closed_when_multi_joker_creation_order_was_never_known():
    run = _run((FlatMultJoker, JollyJoker))
    for joker in run.public.jokers:
        joker.live_id = None
    # Construct a new run after removing ids so no exact order has been retained.
    unknown = HeadlessRunState(public=run.public, seed="AMBER-START")
    assert unknown.joker_order_state is None

    with pytest.raises(HeadlessTransitionError, match="creation order is unavailable"):
        prepare_supported_amber_acorn_start(unknown)


def test_env_r2_amber_start_rejects_wrong_boss_or_disabled_blind():
    run = _run()
    run.public.boss_name = "Verdant Leaf"
    with pytest.raises(HeadlessTransitionError, match="requires Amber Acorn"):
        prepare_supported_amber_acorn_start(run)

    run = _run()
    run.public.blind.disabled = True
    with pytest.raises(HeadlessTransitionError, match="active blind state"):
        prepare_supported_amber_acorn_start(run)
