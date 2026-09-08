from math import comb

from games.balatro.card import BalatroCard
from games.balatro.live.draw_model import PublicCardSignature, PublicDeckComposition
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel


def test_small_public_draw_space_is_enumerated_exactly():
    composition = PublicDeckComposition.from_cards(
        [
            BalatroCard("A", "Spades"),
            BalatroCard("A", "Hearts"),
            BalatroCard("K", "Spades"),
            BalatroCard("2", "Clubs"),
        ]
    )
    model = PublicDrawOutcomeModel(exact_combination_limit=100)

    distribution = model.distribution(composition, draws=2)

    assert distribution.exact is True
    assert distribution.combination_count == comb(4, 2)
    assert len(distribution.outcomes) == 6
    assert abs(sum(outcome.probability for outcome in distribution.outcomes) - 1.0) < 1e-12


def test_duplicate_public_cards_are_weighted_by_physical_card_combinations():
    composition = PublicDeckComposition.from_cards(
        [
            BalatroCard("A", "Spades"),
            BalatroCard("A", "Spades"),
            BalatroCard("K", "Hearts"),
        ]
    )
    model = PublicDrawOutcomeModel(exact_combination_limit=100)

    distribution = model.distribution(composition, draws=1)
    probabilities = {
        outcome.cards: outcome.probability
        for outcome in distribution.outcomes
    }

    ace = (PublicCardSignature("A", "Spades"),)
    king = (PublicCardSignature("K", "Hearts"),)
    assert probabilities[ace] == 2 / 3
    assert probabilities[king] == 1 / 3


def test_large_public_draw_space_uses_reproducible_order_blind_sampling():
    cards = [
        BalatroCard(rank, suit, live_id=index)
        for index, (rank, suit) in enumerate(
            (str(rank), suit)
            for rank in range(2, 12)
            for suit in ("Hearts", "Spades", "Clubs", "Diamonds")
        )
    ]
    first = PublicDeckComposition.from_cards(cards)
    second = PublicDeckComposition.from_cards(list(reversed(cards)))
    model = PublicDrawOutcomeModel(
        exact_combination_limit=10,
        sample_count=64,
        seed=17,
    )

    a = model.distribution(first, draws=5)
    b = model.distribution(second, draws=5)

    assert a.exact is False
    assert a.sample_count == 64
    assert a.outcomes == b.outcomes
    assert abs(sum(outcome.probability for outcome in a.outcomes) - 1.0) < 1e-12


def test_remaining_cards_subtracts_draw_without_using_live_identity():
    composition = PublicDeckComposition.from_cards(
        [
            BalatroCard("A", "Spades", live_id=100),
            BalatroCard("A", "Spades", live_id=200),
            BalatroCard("K", "Hearts", live_id=300),
        ]
    )
    model = PublicDrawOutcomeModel(exact_combination_limit=100)
    distribution = model.distribution(composition, draws=1)
    ace_outcome = next(
        outcome
        for outcome in distribution.outcomes
        if outcome.cards == (PublicCardSignature("A", "Spades"),)
    )

    remaining = model.remaining_cards(composition, ace_outcome)

    assert sorted((card.rank, card.suit) for card in remaining) == [
        ("A", "Spades"),
        ("K", "Hearts"),
    ]
    assert all(card.live_id is None for card in remaining)
