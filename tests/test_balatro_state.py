from games.balatro.card import BalatroCard
from games.balatro.state import BalatroState
from games.balatro.planets import create_planet


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
    assert state.discards_remaining == 3


def test_balatro_state_copy_is_independent():

    state = BalatroState()

    state.money = 10

    copied = state.copy()

    copied.money = 50

    assert state.money == 10
    assert copied.money == 50


def test_balatro_state_copies_consumable_slots():

    state = BalatroState()
    state.consumable_slots = 3

    copied_state = state.copy()

    assert copied_state.consumable_slots == 3


def test_balatro_state_add_and_remove_consumable():

    state = BalatroState()
    consumable = create_planet("MERCURY")

    assert state.add_consumable(
        consumable
    )

    assert consumable in state.consumables

    assert state.remove_consumable(
        consumable
    )

    assert consumable not in state.consumables


def test_balatro_state_rejects_consumable_when_full():

    state = BalatroState()

    first = create_planet("MERCURY")
    second = create_planet("VENUS")
    third = create_planet("EARTH")

    assert state.add_consumable(first)
    assert state.add_consumable(second)
    assert not state.add_consumable(third)