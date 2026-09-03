import pytest

from games.balatro.env import EnvAction
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.jokers.shortcut import ShortcutJoker
from games.balatro.jokers.smeared_joker import SmearedJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.state import BalatroState


PASSIVE_RULE_CASES = (
    (FourFingersJoker, {"flush_size": 4, "straight_size": 4}),
    (PareidoliaJoker, {"all_cards_are_face": True}),
    (ShortcutJoker, {"shortcut": True}),
    (
        SmearedJoker,
        {
            "smeared_suits": {
                "Hearts": "Red",
                "Diamonds": "Red",
                "Clubs": "Black",
                "Spades": "Black",
            }
        },
    ),
    (SplashJoker, {"all_cards_score": True}),
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


@pytest.mark.parametrize(("joker_type", "expected_rules"), PASSIVE_RULE_CASES)
def test_balatro_env_r1_passive_hand_rule_joker_purchase_is_exact(
    joker_type,
    expected_rules,
):
    state = _shop_state()
    state.shop_jokers = [_priced(joker_type)]
    run = HeadlessRunState(public=state, seed=11)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in engine.legal_actions(run)
    next_run = engine.step(run, action)

    # Transition isolation and exact inventory/economy semantics.
    assert run.public.money == 20
    assert run.public.jokers == []
    assert len(run.public.shop_jokers) == 1

    assert next_run.public.money == 15
    assert len(next_run.public.jokers) == 1
    assert type(next_run.public.jokers[0]) is joker_type
    assert next_run.public.shop_jokers == []

    # Passive-rule acquisition must not invent any resource/capacity mutation.
    assert next_run.public.hand_size == 8
    assert next_run.public.hands_remaining == 2
    assert next_run.public.discards_remaining == 1
    assert next_run.public.round_reset_hands_observed is True
    assert next_run.public.round_reset_hands == 4
    assert next_run.public.round_reset_discards_observed is True
    assert next_run.public.round_reset_discards == 3

    rules = hand_rules_for_state(next_run.public)
    for key, value in expected_rules.items():
        assert rules[key] == value


@pytest.mark.parametrize(("joker_type", "_expected_rules"), PASSIVE_RULE_CASES)
def test_balatro_env_r1_passive_hand_rule_editions_remain_fail_closed(
    joker_type,
    _expected_rules,
):
    state = _shop_state()
    joker = _priced(joker_type)
    joker.edition = "Negative"
    state.shop_jokers = [joker]
    run = HeadlessRunState(public=state, seed=12)
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
