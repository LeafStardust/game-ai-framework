from games.balatro.environment import BalatroEnvironment
from games.balatro.actions import (
    PLAY_CARDS,
    BalatroAction
)
from games.dummy import environment


def test_balatro_environment_has_initial_actions():

    environment = BalatroEnvironment()

    actions = environment.get_actions()

    assert len(actions) == 3


def test_PLAY_CARDS_changes_phase():

    environment = BalatroEnvironment()

    action = BalatroAction(
        PLAY_CARDS
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