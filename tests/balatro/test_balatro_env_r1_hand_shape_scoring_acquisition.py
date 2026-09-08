import pytest

from games.balatro.env import EnvAction
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.crazy_joker import CrazyJoker
from games.balatro.jokers.devious_joker import DeviousJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.the_duo import TheDuoJoker
from games.balatro.jokers.the_family import TheFamilyJoker
from games.balatro.jokers.the_order import TheOrderJoker
from games.balatro.jokers.the_tribe import TheTribeJoker
from games.balatro.jokers.the_trio import TheTrioJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.state import BalatroState


PURE_SCORING_TYPES = (
    JollyJoker,
    SlyJoker,
    ZanyJoker,
    WilyJoker,
    TheDuoJoker,
    CrazyJoker,
    DeviousJoker,
    DrollJoker,
    CraftyJoker,
    MadJoker,
    CleverJoker,
    TheTrioJoker,
    TheFamilyJoker,
    TheOrderJoker,
    TheTribeJoker,
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


@pytest.mark.parametrize("joker_type", PURE_SCORING_TYPES)
def test_balatro_env_r1_hand_shape_scoring_purchase_is_exact_inventory_only(joker_type):
    state = _shop_state()
    state.shop_jokers = [_priced(joker_type)]
    run = HeadlessRunState(public=state, seed=21)
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


@pytest.mark.parametrize("joker_type", PURE_SCORING_TYPES)
def test_balatro_env_r1_hand_shape_scoring_editions_remain_fail_closed(joker_type):
    state = _shop_state()
    joker = _priced(joker_type)
    joker.edition = "Negative"
    state.shop_jokers = [joker]
    run = HeadlessRunState(public=state, seed=22)
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
