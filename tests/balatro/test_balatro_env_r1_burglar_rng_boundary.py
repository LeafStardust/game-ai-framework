import pytest

from games.balatro.env import EnvAction
from games.balatro.env.transition import HeadlessRunState, ShopTransitionEngine
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.state import BalatroState


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


def test_balatro_env_r1_burglar_purchase_remains_fail_closed_until_blind_start_is_owned():
    state = _shop_state()
    burglar = BurglarJoker()
    burglar.cost = 6
    state.shop_jokers = [burglar]
    run = HeadlessRunState(public=state, seed=37)
    engine = ShopTransitionEngine()
    buy = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert buy not in engine.legal_actions(run)


def test_balatro_env_r1_select_blind_remains_outside_training_surface_until_r2_rng():
    with pytest.raises(ValueError, match="action SELECT_BLIND is not training-exposed"):
        EnvAction.from_alias("SELECT_BLIND")
