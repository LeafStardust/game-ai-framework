import pytest

from games.balatro.env import EnvAction
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.jokers.troubadour import TroubadourJoker
from games.balatro.state import BalatroState


def _shop_state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 20
    return state


def _troubadour(*, cost: int = 5) -> TroubadourJoker:
    joker = TroubadourJoker()
    joker.label = "Troubadour"
    joker.cost = cost
    return joker


def test_balatro_state_copies_observed_next_round_hands():
    state = _shop_state()
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4

    copied = state.copy()

    assert copied.round_reset_hands_observed is True
    assert copied.round_reset_hands == 4


def test_balatro_env_r1_state_validates_observed_round_reset_hands():
    state = _shop_state()
    state.round_reset_hands_observed = "yes"
    with pytest.raises(
        HeadlessTransitionError,
        match="round_reset_hands_observed must be a boolean",
    ):
        HeadlessRunState(public=state, seed=1)

    state = _shop_state()
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4.0
    with pytest.raises(
        HeadlessTransitionError,
        match="round_reset_hands must be an exact integer",
    ):
        HeadlessRunState(public=state, seed=1)

    state.round_reset_hands = -1
    with pytest.raises(
        HeadlessTransitionError,
        match="round_reset_hands cannot be negative",
    ):
        HeadlessRunState(public=state, seed=1)


def test_balatro_env_r1_troubadour_remains_fail_closed_without_reset_hands_observation():
    state = _shop_state()
    state.shop_jokers = [_troubadour()]
    state.hand_size = 8
    state.hands_remaining = 2
    run = HeadlessRunState(public=state, seed=2)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition: BUY_JOKER"):
        engine.step(run, action)

    assert run.public.money == 20
    assert run.public.hand_size == 8
    assert run.public.hands_remaining == 2
    assert run.public.round_reset_hands == 0
    assert run.public.jokers == []


def test_balatro_env_r1_troubadour_remains_fail_closed_at_zero_reset_hands():
    state = _shop_state()
    state.shop_jokers = [_troubadour()]
    state.round_reset_hands_observed = True
    state.round_reset_hands = 0
    run = HeadlessRunState(public=state, seed=3)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition: BUY_JOKER"):
        engine.step(run, action)

    assert run.public.money == 20
    assert run.public.hand_size == 8
    assert run.public.round_reset_hands == 0
    assert run.public.jokers == []


def test_balatro_env_r1_troubadour_updates_next_round_hands_and_hand_size_once():
    state = _shop_state()
    state.shop_jokers = [_troubadour()]
    state.hand_size = 8
    state.hands_remaining = 2
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    run = HeadlessRunState(public=state, seed=4)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in engine.legal_actions(run)
    next_run = engine.step(run, action)

    assert run.public.money == 20
    assert run.public.hand_size == 8
    assert run.public.hands_remaining == 2
    assert run.public.round_reset_hands == 4
    assert run.public.jokers == []

    assert next_run.public.money == 15
    assert next_run.public.hand_size == 10
    assert next_run.public.hands_remaining == 2
    assert next_run.public.round_reset_hands_observed is True
    assert next_run.public.round_reset_hands == 3
    assert len(next_run.public.jokers) == 1
    assert type(next_run.public.jokers[0]) is TroubadourJoker
    assert next_run.public.shop_jokers == []
