from dataclasses import dataclass
from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.boss_hand_constraint_policy import (
    _eye_filter,
    _mouth_filter,
    _mouth_forced_discard,
    _psychic_filter,
)
from games.balatro.card import BalatroCard
from games.balatro.hand_evaluator import HandEvaluator


def _plan(name, cards=()):
    return SimpleNamespace(action=BalatroAction(name, cards=list(cards)))


def test_psychic_keeps_short_and_five_card_plays_legal():
    cards = [BalatroCard(str(rank), "Hearts") for rank in ("2", "3", "4", "5", "6")]
    five = _plan(PLAY_CARDS, cards)
    four = _plan(PLAY_CARDS, cards[:4])
    discard = _plan(DISCARD_CARDS, cards[:2])
    state = SimpleNamespace(boss_name="The Psychic", jokers=[])

    result = _psychic_filter(state, (four, five, discard))

    assert result == (four, five, discard)


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


def test_locked_mouth_filters_other_play_types_while_discards_exist():
    straight = _plan(
        PLAY_CARDS,
        [BalatroCard(rank, "Hearts") for rank in ("10", "J", "Q", "K", "A")],
    )
    pair = _plan(
        PLAY_CARDS,
        [BalatroCard("Q", "Hearts"), BalatroCard("Q", "Spades")],
    )
    discard = _plan(DISCARD_CARDS, [BalatroCard("2", "Clubs")])
    state = SimpleNamespace(
        boss_name="The Mouth",
        boss_blind_only_hand="STRAIGHT",
        jokers=[],
    )
    policy = SimpleNamespace(_hand_evaluator=HandEvaluator())

    result = _mouth_filter(policy, state, (pair, straight, discard))

    assert result == (straight, discard)


def test_locked_mouth_widens_equal_structure_discard_instead_of_preserving_duplicates():
    hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Hearts"),
        BalatroCard("J", "Clubs"),
        BalatroCard("J", "Diamonds"),
        BalatroCard("3", "Spades"),
    ]
    narrow = _plan(DISCARD_CARDS, [hand[-1]])
    wide = _plan(DISCARD_CARDS, [hand[2], hand[5], hand[6], hand[7]])
    state = SimpleNamespace(
        boss_name="The Mouth",
        boss_blind_only_hand="STRAIGHT",
        jokers=[],
        hand=hand,
    )
    evaluator = SimpleNamespace(evaluate=lambda state, action: float(len(action.cards)))
    policy = SimpleNamespace(
        _hand_evaluator=HandEvaluator(),
        _structure_fit=StrategyAwareLiveHandActionPolicy._structure_fit,
        _within_type_key=lambda plan: (0.0,),
        evaluator=evaluator,
        EPSILON=1e-9,
    )
    @dataclass(frozen=True)
    class Decision:
        action: object
        selected_plan: object
        confidence: float = 0.5
        rationale: tuple[str, ...] = ()
        mode: str = "PACE_RECOVERY"
        selected_immediate_score: float | None = None
        selected_pace_ratio: float | None = None
        selected_fallback_value: float | None = 1.0

    decision = Decision(action=narrow.action, selected_plan=narrow)

    result = _mouth_forced_discard(policy, state, (narrow, wide), decision)

    assert result.action is wide.action
    assert any("redraw width=4" in note for note in result.rationale)
