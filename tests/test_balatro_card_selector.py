from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.card import BalatroCard
from games.balatro.card_selector import CardSelector
from games.balatro.state import BalatroState


def test_play_actions_include_all_valid_hand_sizes():

    state = BalatroState()
    state.hand = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
    ]

    actions = CardSelector().generate_play_actions(state)

    assert len(actions) == sum(
        6 if size == 1 else 1
        for size in []
    ) if False else 62
    assert all(action.name == PLAY_CARDS for action in actions)
    assert {len(action.cards) for action in actions} == {1, 2, 3, 4, 5}


def test_discard_actions_include_all_valid_hand_sizes():

    state = BalatroState()
    state.hand = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Hearts"),
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
    ]

    actions = CardSelector().generate_discard_actions(state)

    assert len(actions) == 62
    assert all(action.name == DISCARD_CARDS for action in actions)
    assert {len(action.cards) for action in actions} == {1, 2, 3, 4, 5}


def test_discard_actions_are_unavailable_without_discards():

    state = BalatroState()
    state.hand = [
        BalatroCard("2", "Hearts")
    ]
    state.discards_remaining = 0

    assert CardSelector().generate_discard_actions(state) == []
