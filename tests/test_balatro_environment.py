from games.balatro.environment import BalatroEnvironment
from games.balatro.actions import (
    PLAY_HAND,
    BalatroAction
)


def test_balatro_environment_has_initial_actions():

    environment = BalatroEnvironment()

    actions = environment.get_actions()

    assert len(actions) == 3


def test_play_hand_changes_phase():

    environment = BalatroEnvironment()

    action = BalatroAction(
        PLAY_HAND
    )

    environment.execute_action(
        action
    )

    assert environment.state.phase == "ROUND_END"


def test_end_round_increases_round():

    environment = BalatroEnvironment()

    action = BalatroAction(
        "END_ROUND"
    )

    environment.execute_action(
        action
    )

    assert environment.state.round == 2