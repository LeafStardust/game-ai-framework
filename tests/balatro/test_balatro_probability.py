from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.probability import HandProbability


def test_best_hand_finds_strongest_subset():

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Clubs"),
        BalatroCard("A", "Diamonds"),
        BalatroCard("K", "Spades"),
        BalatroCard("2", "Hearts"),
        BalatroCard("7", "Clubs"),
    ]

    assert HandProbability().best_hand(cards) == PokerHand.THREE_OF_A_KIND


def test_hand_distribution_counts_best_hands():

    probability = HandProbability()

    class State:
        def __init__(self, hand):
            self.hand = hand

    states = [
        State([
            BalatroCard("A", "Hearts"),
            BalatroCard("A", "Clubs"),
        ]),
        State([
            BalatroCard("2", "Hearts"),
        ]),
    ]

    distribution = probability.hand_distribution(states)

    assert distribution[PokerHand.PAIR] == 0.5
    assert distribution[PokerHand.HIGH_CARD] == 0.5


def test_hand_probability_returns_selected_probability():

    probability = HandProbability()

    class State:
        def __init__(self, hand):
            self.hand = hand

    states = [
        State([
            BalatroCard("A", "Hearts"),
            BalatroCard("A", "Clubs"),
        ]),
        State([
            BalatroCard("2", "Hearts"),
        ]),
    ]

    assert probability.hand_probability(
        states,
        PokerHand.PAIR
    ) == 0.5
