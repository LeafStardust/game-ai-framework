from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.jokers.shortcut import ShortcutJoker
from games.balatro.jokers.smeared_joker import SmearedJoker
from games.balatro.jokers.the_duo import TheDuoJoker
from games.balatro.jokers.the_family import TheFamilyJoker
from games.balatro.jokers.the_order import TheOrderJoker
from games.balatro.jokers.the_tribe import TheTribeJoker
from games.balatro.jokers.the_trio import TheTrioJoker
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


def test_duo_triggers_when_flush_contains_pair():
    cards = [
        BalatroCard("9", "Hearts"),
        BalatroCard("9", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("3", "Hearts"),
    ]

    hand, score = _project(cards, [TheDuoJoker()])

    assert hand == PokerHand.FLUSH
    assert score == 544


def test_trio_triggers_when_full_house_contains_three_of_a_kind():
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Hearts"),
        BalatroCard("10", "Diamonds"),
        BalatroCard("9", "Clubs"),
        BalatroCard("9", "Spades"),
    ]

    hand, score = _project(cards, [TheTrioJoker()])

    assert hand == PokerHand.FULL_HOUSE
    assert score == 1056


def test_family_triggers_on_four_of_a_kind():
    cards = [
        BalatroCard("8", "Spades"),
        BalatroCard("8", "Hearts"),
        BalatroCard("8", "Diamonds"),
        BalatroCard("8", "Clubs"),
        BalatroCard("K", "Spades"),
    ]

    hand, score = _project(cards, [TheFamilyJoker()])

    assert hand == PokerHand.FOUR_OF_A_KIND
    assert score == 2576


def test_order_triggers_when_straight_flush_contains_straight():
    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
    ]

    hand, score = _project(cards, [TheOrderJoker()])

    assert hand == PokerHand.STRAIGHT_FLUSH
    assert score == 2880


def test_tribe_triggers_when_straight_flush_contains_flush():
    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
    ]

    hand, score = _project(cards, [TheTribeJoker()])

    assert hand == PokerHand.STRAIGHT_FLUSH
    assert score == 1920


def test_order_uses_shortcut_straight_rules():
    cards = [
        BalatroCard("2", "Spades"),
        BalatroCard("4", "Hearts"),
        BalatroCard("6", "Diamonds"),
        BalatroCard("8", "Clubs"),
        BalatroCard("10", "Spades"),
    ]

    hand, score = _project(cards, [ShortcutJoker(), TheOrderJoker()])

    assert hand == PokerHand.STRAIGHT
    assert score == 720


def test_tribe_uses_smeared_flush_rules():
    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("6", "Hearts"),
        BalatroCard("8", "Diamonds"),
        BalatroCard("10", "Hearts"),
    ]

    hand, score = _project(cards, [SmearedJoker(), TheTribeJoker()])

    assert hand == PokerHand.FLUSH
    assert score == 520


def test_duo_trio_family_stack_on_four_of_a_kind_containment():
    cards = [
        BalatroCard("8", "Spades"),
        BalatroCard("8", "Hearts"),
        BalatroCard("8", "Diamonds"),
        BalatroCard("8", "Clubs"),
        BalatroCard("K", "Spades"),
    ]

    hand, score = _project(
        cards,
        [TheDuoJoker(), TheTrioJoker(), TheFamilyJoker()],
    )

    assert hand == PokerHand.FOUR_OF_A_KIND
    assert score == 15456
