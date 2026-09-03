import pytest

from games.balatro.env import EnvAction
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.jokers.merry_andy import MerryAndyJoker
from games.balatro.state import BalatroState


def _shop_state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 20
    return state


def _merry_andy(*, cost: int = 7) -> MerryAndyJoker:
    joker = MerryAndyJoker()
    joker.label = "Merry Andy"
    joker.cost = cost
    return joker


def test_balatro_env_r1_merry_andy_remains_fail_closed_without_reset_discards_observation():
    state = _shop_state()
    state.shop_jokers = [_merry_andy()]
    state.hand_size = 8
    state.discards_remaining = 1
    run = HeadlessRunState(public=state, seed=1)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition: BUY_JOKER"):
        engine.step(run, action)

    assert run.public.money == 20
    assert run.public.hand_size == 8
    assert run.public.discards_remaining == 1
    assert run.public.round_reset_discards == 0
    assert run.public.jokers == []


def test_balatro_env_r1_merry_andy_remains_fail_closed_at_zero_hand_size():
    state = _shop_state()
    state.shop_jokers = [_merry_andy()]
    state.hand_size = 0
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    run = HeadlessRunState(public=state, seed=2)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition: BUY_JOKER"):
        engine.step(run, action)

    assert run.public.money == 20
    assert run.public.hand_size == 0
    assert run.public.round_reset_discards == 3
    assert run.public.jokers == []


def test_balatro_env_r1_merry_andy_updates_next_round_discards_and_hand_size_once():
    state = _shop_state()
    state.shop_jokers = [_merry_andy()]
    state.hand_size = 8
    state.discards_remaining = 1
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    run = HeadlessRunState(public=state, seed=3)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in engine.legal_actions(run)
    next_run = engine.step(run, action)

    assert run.public.money == 20
    assert run.public.hand_size == 8
    assert run.public.discards_remaining == 1
    assert run.public.round_reset_discards == 3
    assert run.public.jokers == []

    assert next_run.public.money == 13
    assert next_run.public.hand_size == 7
    assert next_run.public.discards_remaining == 1
    assert next_run.public.round_reset_discards_observed is True
    assert next_run.public.round_reset_discards == 6
    assert len(next_run.public.jokers) == 1
    assert type(next_run.public.jokers[0]) is MerryAndyJoker
    assert next_run.public.shop_jokers == []
