from math import comb

from games.balatro.card import BalatroCard
from games.balatro.live.draw_model import PublicCardSignature, PublicDeckComposition
from games.balatro.state import BalatroState


def test_public_composition_ignores_card_identity_and_input_order():
    first = [
        BalatroCard("A", "Spades", live_id=900),
        BalatroCard("K", "Hearts", live_id=901),
        BalatroCard("A", "Spades", live_id=902),
    ]
    second = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("A", "Spades", live_id=2),
        BalatroCard("K", "Hearts", live_id=3),
    ]

    a = PublicDeckComposition.from_cards(first)
    b = PublicDeckComposition.from_cards(second)

    assert a.items() == b.items()
    assert a.total_cards == 3
    assert a.unique_signatures == 2
    assert a.count(PublicCardSignature("A", "Spades")) == 2


def test_public_signature_preserves_visible_modifiers_but_not_live_id():
    a = BalatroCard(
        "7",
        "Diamonds",
        enhancement="Lucky",
        edition="Foil",
        seal="Red",
        live_id=12,
    )
    b = BalatroCard(
        "7",
        "Diamonds",
        enhancement="Lucky",
        edition="Foil",
        seal="Red",
        live_id=999,
    )

    assert PublicCardSignature.from_card(a) == PublicCardSignature.from_card(b)
    assert PublicCardSignature.from_card(a) == PublicCardSignature(
        "7",
        "Diamonds",
        "Lucky",
        "Foil",
        "Red",
    )


def test_aggregate_output_sorts_mixed_modified_and_unmodified_same_card():
    composition = PublicDeckComposition.from_cards(
        [
            BalatroCard("7", "Diamonds", enhancement="Lucky"),
            BalatroCard("7", "Diamonds"),
            BalatroCard("7", "Diamonds", edition="Foil"),
        ]
    )

    items = composition.items()

    assert len(items) == 3
    assert {signature.enhancement for signature, _ in items} == {None, "Lucky"}
    assert {signature.edition for signature, _ in items} == {None, "Foil"}


def test_exact_hypergeometric_probability_uses_without_replacement_math():
    cards = [BalatroCard("A", "Spades") for _ in range(4)] + [
        BalatroCard("2", "Hearts") for _ in range(6)
    ]
    composition = PublicDeckComposition.from_cards(cards)

    probability = composition.probability_exact_matches(
        matching_cards=4,
        draws=3,
        matches=2,
    )

    expected = comb(4, 2) * comb(6, 1) / comb(10, 3)
    assert abs(probability - expected) < 1e-12


def test_at_least_probability_matches_sum_of_exact_distribution():
    cards = [BalatroCard("A", "Spades") for _ in range(4)] + [
        BalatroCard("2", "Hearts") for _ in range(6)
    ]
    composition = PublicDeckComposition.from_cards(cards)

    distribution = composition.draw_count_distribution(4, 3)
    probability = composition.probability_at_least_matches(4, 3, 2)

    assert abs(sum(outcome.probability for outcome in distribution) - 1.0) < 1e-12
    assert abs(
        probability
        - sum(outcome.probability for outcome in distribution if outcome.matches >= 2)
    ) < 1e-12


def test_rank_and_suit_queries_operate_on_unordered_composition():
    state = BalatroState()
    state.deck = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("A", "Hearts", live_id=2),
        BalatroCard("K", "Spades", live_id=3),
        BalatroCard("Q", "Clubs", live_id=4),
    ]
    composition = PublicDeckComposition.from_state(state)

    # One draw from four cards: 2 Aces and 2 Spades.
    assert composition.probability_rank("A", draws=1) == 0.5
    assert composition.probability_suit("Spades", draws=1) == 0.5


def test_drawing_more_than_remaining_deck_is_clamped_to_all_cards():
    composition = PublicDeckComposition.from_cards(
        [BalatroCard("A", "Spades"), BalatroCard("2", "Hearts")]
    )

    assert composition.probability_rank("A", draws=5) == 1.0
    distribution = composition.draw_count_distribution(1, 5)
    assert [(outcome.matches, outcome.probability) for outcome in distribution] == [
        (1, 1.0)
    ]
