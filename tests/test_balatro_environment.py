from games.balatro.card import BalatroCard
from games.balatro.environment import BalatroEnvironment
from games.balatro.actions import (
    PLAY_CARDS,
    BalatroAction
)


def test_balatro_environment_has_initial_actions():

    environment = BalatroEnvironment()

    actions = environment.get_actions()

    assert len(actions) == 2


def test_PLAY_CARDS_changes_phase():

    environment = BalatroEnvironment()

    action = BalatroAction(
        PLAY_CARDS,
        cards=[
            BalatroCard("A", "Hearts"),
            BalatroCard("K", "Hearts"),
            BalatroCard("Q", "Hearts"),
            BalatroCard("J", "Hearts"),
            BalatroCard("10", "Hearts")
        ]
    )

    environment.execute_action(
        action
    )

    assert environment.state.phase == "ROUND_START"
    assert environment.state.round == 2


def test_end_round_increases_round():

    environment = BalatroEnvironment()

    action = BalatroAction(
        "END_ROUND"
    )

    environment.execute_action(
        action
    )

    assert environment.state.round == 2


def test_balatro_environment_generates_play_actions():

    environment = BalatroEnvironment()

    environment.state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Hearts"),
        BalatroCard("10", "Hearts")
    ]

    actions = environment.get_actions()

    play_actions = [
        action
        for action in actions
        if action.name == "PLAY_CARDS"
    ]

    assert len(play_actions) == 1