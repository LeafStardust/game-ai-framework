from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.crazy_joker import CrazyJoker
from games.balatro.jokers.devious_joker import DeviousJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.shortcut import ShortcutJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.smeared_joker import SmearedJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _project(cards, jokers):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.jokers = list(jokers)

    rules = hand_rules_for_state(state)
    hand = HandEvaluator().evaluate(list(cards), rules=rules)
    transition = VisibleCardScoreOutcomeModel().project_transition(
        hand,
        state,
        list(cards),
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    return hand, transition.distribution.minimum


def test_pair_jokers_trigger_when_flush_contains_pair():
    cards = [
        BalatroCard("7", "Hearts"),
        BalatroCard("7", "Diamonds", enhancement="Wild"),
        BalatroCard("2", "Hearts"),
        BalatroCard("4", "Hearts"),
        BalatroCard("6", "Hearts"),
    ]

    hand, score = _project(cards, [JollyJoker(), SlyJoker()])

    assert hand == PokerHand.FLUSH
    assert score == 1332


def test_full_house_contains_three_of_a_kind_and_two_pair():
    cards = [
        BalatroCard("7", "Hearts"),
        BalatroCard("7", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("2", "Diamonds"),
        BalatroCard("2", "Hearts"),
    ]

    hand, score = _project(
        cards,
        [WilyJoker(), ZanyJoker(), CleverJoker(), MadJoker()],
    )

    assert hand == PokerHand.FULL_HOUSE
    assert score == 6370


def test_shortcut_straight_triggers_crazy_and_devious():
    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("4", "Spades"),
        BalatroCard("6", "Diamonds"),
        BalatroCard("8", "Clubs"),
        BalatroCard("10", "Hearts"),
    ]

    hand, score = _project(cards, [ShortcutJoker(), CrazyJoker(), DeviousJoker()])

    assert hand == PokerHand.STRAIGHT
    assert score == 2560


def test_four_fingers_flush_triggers_crafty_and_droll_with_off_suit_kicker():
    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("4", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("8", "Hearts"),
        BalatroCard("K", "Clubs"),
    ]

    hand, score = _project(cards, [FourFingersJoker(), CraftyJoker(), DrollJoker()])

    assert hand == PokerHand.FLUSH
    assert score == 1890


def test_smeared_flush_triggers_crafty_and_droll_across_red_suits():
    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("6", "Hearts"),
        BalatroCard("8", "Diamonds"),
        BalatroCard("10", "Hearts"),
    ]

    hand, score = _project(cards, [SmearedJoker(), CraftyJoker(), DrollJoker()])

    assert hand == PokerHand.FLUSH
    assert score == 2030


def test_stone_card_rank_does_not_create_pair_containment():
    evaluator = HandEvaluator()
    cards = [
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Hearts", enhancement="Stone"),
    ]

    assert evaluator.contains(cards, PokerHand.PAIR) is False
