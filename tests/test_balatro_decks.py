from games.balatro.decks import BASE_DECK, RED_DECK
from games.balatro.environment import BalatroEnvironment


def test_red_deck_starts_with_four_discards():

    environment = BalatroEnvironment(RED_DECK)

    assert environment.state.deck_name == "RED"
    assert environment.state.discards_remaining == 4
    assert environment.state.hand_size == 8
    assert environment.state.money == 0


def test_base_deck_keeps_default_starting_rules():

    environment = BalatroEnvironment(BASE_DECK)

    assert environment.state.deck_name == "BASE"
    assert environment.state.discards_remaining == 3
    assert environment.state.hand_size == 8
    assert environment.state.money == 0


def test_red_deck_reset_restores_deck_rules():

    environment = BalatroEnvironment(RED_DECK)
    environment.state.discards_remaining = 0
    environment.state.money = 20

    environment.reset()

    assert environment.state.deck_name == "RED"
    assert environment.state.discards_remaining == 4
    assert environment.state.hand_size == 8
    assert environment.state.money == 0
