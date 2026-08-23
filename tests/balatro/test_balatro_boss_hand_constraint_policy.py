from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.boss_hand_constraint_policy import _eye_filter, _psychic_filter
from games.balatro.card import BalatroCard
from games.balatro.hand_evaluator import HandEvaluator


def _plan(name, cards=()):
    return SimpleNamespace(action=BalatroAction(name, cards=list(cards)))


def test_psychic_filters_non_five_card_plays_but_keeps_discards():
    cards = [BalatroCard(str(rank), "Hearts") for rank in ("2", "3", "4", "5", "6")]
    five = _plan(PLAY_CARDS, cards)
    four = _plan(PLAY_CARDS, cards[:4])
    discard = _plan(DISCARD_CARDS, cards[:2])
    state = SimpleNamespace(boss_name="The Psychic", jokers=[])

    result = _psychic_filter(state, (four, five, discard))

    assert five in result
    assert discard in result
    assert four not in result


def test_eye_filters_already_used_hand_type_when_unused_play_exists():
    pair_cards = [
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Clubs"),
    ]
    high_cards = [BalatroCard("A", "Spades")]
    pair = _plan(PLAY_CARDS, pair_cards)
    high = _plan(PLAY_CARDS, high_cards)
    discard = _plan(DISCARD_CARDS, high_cards)
    state = SimpleNamespace(
        boss_name="The Eye",
        jokers=[],
        boss_blind_hands={"PAIR"},
        boss_blind_state_observed=True,
        round_hand_play_counts={},
    )
    policy = SimpleNamespace(_hand_evaluator=HandEvaluator())

    result = _eye_filter(policy, state, (pair, high, discard))

    assert high in result
    assert discard in result
    assert pair not in result


def test_eye_falls_back_to_round_history_only_when_blind_table_unobserved():
    pair_cards = [
        BalatroCard("Q", "Hearts"),
        BalatroCard("Q", "Spades"),
    ]
    pair = _plan(PLAY_CARDS, pair_cards)
    high = _plan(PLAY_CARDS, [BalatroCard("A", "Clubs")])
    state = SimpleNamespace(
        boss_name="The Eye",
        jokers=[],
        boss_blind_hands=set(),
        boss_blind_state_observed=False,
        round_hand_play_counts={"PAIR": 1},
    )
    policy = SimpleNamespace(_hand_evaluator=HandEvaluator())

    result = _eye_filter(policy, state, (pair, high))

    assert high in result
    assert pair not in result
