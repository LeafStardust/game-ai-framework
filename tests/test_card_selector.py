from math import comb

from games.balatro.card import BalatroCard
from games.balatro.card_selector import CardSelector
from games.balatro.state import BalatroState


def test_card_selector_generates_play_options():

    state = BalatroState()

    state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Hearts"),
        BalatroCard("10", "Hearts"),
        BalatroCard("9", "Clubs")
    ]

    selector = CardSelector()

    actions = selector.generate_actions(
        state
    )

    play_actions = [
        action
        for action in actions
        if action.name == "PLAY_CARDS"
    ]

    assert len(play_actions) == sum(
        comb(6, size)
        for size in range(1, 6)
    )


def test_card_selector_generates_discard_options():

    state = BalatroState()

    state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Hearts"),
        BalatroCard("10", "Hearts"),
        BalatroCard("9", "Clubs")
    ]

    selector = CardSelector()

    actions = selector.generate_actions(
        state
    )

    discard_actions = [
        action
        for action in actions
        if action.name == "DISCARD_CARDS"
    ]

    assert len(discard_actions) == sum(
        comb(6, size)
        for size in range(1, 6)
    )
