import pytest

from games.balatro.env import EnvAction
from games.balatro.env.transition import HeadlessRunState, ShopTransitionEngine
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.walkie_talkie import WalkieTalkieJoker
from games.balatro.state import BalatroState


def _shop_state(joker_type):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 20
    joker = joker_type()
    joker.cost = 5
    state.shop_jokers = [joker]
    return state


@pytest.mark.parametrize("joker_type", (HalfJoker, WalkieTalkieJoker, PhotographJoker))
def test_r1_scoring_only_joker_acquisition_is_exact(joker_type):
    state = _shop_state(joker_type)
    run = HeadlessRunState(public=state, seed=21)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)

    next_run = engine.step(run, action)

    assert run.public.money == 20
    assert run.public.jokers == []
    assert len(run.public.shop_jokers) == 1
    assert next_run.public.money == 15
    assert len(next_run.public.jokers) == 1
    assert type(next_run.public.jokers[0]) is joker_type
    assert next_run.public.shop_jokers == []
