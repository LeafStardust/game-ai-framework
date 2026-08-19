from games.balatro.card import BalatroCard
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand import PokerHand


def test_high_card_detection():

    evaluator = HandEvaluator()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Spades"),
        BalatroCard("7", "Clubs"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    result = evaluator.evaluate(
        cards
    )

    assert result == PokerHand.HIGH_CARD


def test_pair_detection():

    evaluator = HandEvaluator()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Clubs")
    ]

    result = evaluator.evaluate(
        cards
    )

    assert result == PokerHand.PAIR


def test_two_pair_detection():

    evaluator = HandEvaluator()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Clubs"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    result = evaluator.evaluate(
        cards
    )

    assert result == PokerHand.TWO_PAIR


def test_three_of_a_kind_detection():

    evaluator = HandEvaluator()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Clubs"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    result = evaluator.evaluate(
        cards
    )

    assert result == PokerHand.THREE_OF_A_KIND


def test_straight_detection():

    evaluator = HandEvaluator()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Clubs"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("6", "Hearts")
    ]

    result = evaluator.evaluate(
        cards
    )

    assert result == PokerHand.STRAIGHT


def test_flush_detection():

    evaluator = HandEvaluator()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("2", "Hearts")
    ]

    result = evaluator.evaluate(
        cards
    )

    assert result == PokerHand.FLUSH


def test_full_house_detection():

    evaluator = HandEvaluator()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Clubs"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("K", "Clubs")
    ]

    result = evaluator.evaluate(
        cards
    )

    assert result == PokerHand.FULL_HOUSE


def test_four_of_a_kind_detection():

    evaluator = HandEvaluator()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Clubs"),
        BalatroCard("A", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    result = evaluator.evaluate(
        cards
    )

    assert result == PokerHand.FOUR_OF_A_KIND


def test_straight_flush_detection():

    evaluator = HandEvaluator()

    cards = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts")
    ]

    result = evaluator.evaluate(
        cards
    )

    assert result == PokerHand.STRAIGHT_FLUSH


def test_single_card_is_high_card():

    result = HandEvaluator().evaluate([
        BalatroCard("A", "Hearts")
    ])

    assert result == PokerHand.HIGH_CARD


def test_pair_can_be_evaluated_with_two_cards():

    result = HandEvaluator().evaluate([
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Clubs")
    ])

    assert result == PokerHand.PAIR


def test_four_of_a_kind_can_be_evaluated_with_four_cards():

    result = HandEvaluator().evaluate([
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Clubs"),
        BalatroCard("A", "Diamonds"),
        BalatroCard("A", "Spades")
    ])

    assert result == PokerHand.FOUR_OF_A_KIND


def test_ace_low_straight_is_recognized():

    result = HandEvaluator().evaluate([
        BalatroCard("A", "Hearts"),
        BalatroCard("2", "Clubs"),
        BalatroCard("3", "Diamonds"),
        BalatroCard("4", "Spades"),
        BalatroCard("5", "Hearts")
    ])

    assert result == PokerHand.STRAIGHT
