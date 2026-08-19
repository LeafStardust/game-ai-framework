from types import SimpleNamespace

from games.balatro.jokers.card_sharp import CardSharpJoker
from games.balatro.jokers.the_duo import TheDuoJoker
from games.balatro.strategy import NEUTRAL, SILVER
from games.balatro.strategy_conditional_relationships import conditional_joker_relationship


def _state(*, jokers=(), hand_levels=None):
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=[],
        owned_deck=[],
        deck=[],
        hand_levels=dict(hand_levels or {}),
        hand_play_counts={},
        ante=2,
    )


def test_card_sharp_does_not_seed_pair_strategy_by_itself():
    state = _state(jokers=(CardSharpJoker(),))
    assert conditional_joker_relationship(state, "pair", CardSharpJoker()) == NEUTRAL


def test_card_sharp_is_silver_once_pair_route_is_established():
    state = _state(jokers=(TheDuoJoker(), CardSharpJoker()))
    assert conditional_joker_relationship(state, "pair", CardSharpJoker()) == SILVER


def test_card_sharp_is_silver_for_invested_poker_hand_route():
    state = _state(jokers=(CardSharpJoker(),), hand_levels={"STRAIGHT": 2})
    assert conditional_joker_relationship(state, "straight", CardSharpJoker()) == SILVER
