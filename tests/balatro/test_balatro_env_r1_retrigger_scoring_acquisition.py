import pytest

from games.balatro.env import EnvAction
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.jokers.dusk import DuskJoker
from games.balatro.jokers.hack import HackJoker
from games.balatro.jokers.hanging_chad import HangingChadJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.sock_and_buskin import SockAndBuskinJoker
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.state import BalatroState


RETRIGGER_SCORING_TYPES = (
    DuskJoker,
    HackJoker,
    HangingChadJoker,
    MimeJoker,
    SockAndBuskinJoker,
)


def _shop_state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 20
    state.hand_size = 8
    state.hands_remaining = 2
    state.discards_remaining = 1
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return state


def _priced(joker_type):
    joker = joker_type()
    joker.cost = 5
    return joker


@pytest.mark.parametrize("joker_type", RETRIGGER_SCORING_TYPES)
def test_balatro_env_r1_retrigger_scoring_purchase_is_exact_inventory_only(joker_type):
    state = _shop_state()
    state.shop_jokers = [_priced(joker_type)]
    run = HeadlessRunState(public=state, seed=40)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert joker_type.__name__ in LiveJokerScoreProjector.SUPPORTED_CLASS_NAMES
    assert action in engine.legal_actions(run)

    next_run = engine.step(run, action)

    assert run.public.money == 20
    assert run.public.jokers == []
    assert len(run.public.shop_jokers) == 1

    assert next_run.public.money == 15
    assert len(next_run.public.jokers) == 1
    assert type(next_run.public.jokers[0]) is joker_type
    assert next_run.public.shop_jokers == []

    assert next_run.public.hand_size == 8
    assert next_run.public.hands_remaining == 2
    assert next_run.public.discards_remaining == 1
    assert next_run.public.round_reset_hands == 4
    assert next_run.public.round_reset_discards == 3


@pytest.mark.parametrize("joker_type", RETRIGGER_SCORING_TYPES)
def test_balatro_env_r1_retrigger_scoring_editions_remain_fail_closed(joker_type):
    state = _shop_state()
    joker = _priced(joker_type)
    joker.edition = "Negative"
    state.shop_jokers = [joker]
    run = HeadlessRunState(public=state, seed=41)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(run)
    with pytest.raises(
        HeadlessTransitionError,
        match="illegal shop transition: BUY_JOKER",
    ):
        engine.step(run, action)

    assert run.public.money == 20
    assert run.public.jokers == []
    assert len(run.public.shop_jokers) == 1
