from games.balatro.card import BalatroCard
from games.balatro.state import BalatroState


def test_balatro_card_creation():

    card = BalatroCard(
        "A",
        "Hearts"
    )

    assert card.rank == "A"
    assert card.suit == "Hearts"


def test_balatro_state_creation():

    state = BalatroState()

    state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Spades")
    ]

    assert len(state.hand) == 2
    assert state.deck_size == 52
    assert state.discard_count == 0