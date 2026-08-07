from games.balatro.card import BalatroCard
from games.balatro.environment import BalatroEnvironment
from games.balatro.actions import (
    DISCARD_CARDS,
    END_ROUND,
    PLAY_CARDS,
    BalatroAction
)


def test_balatro_environment_has_initial_actions():

    environment = BalatroEnvironment()

    environment.state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Hearts"),
        BalatroCard("10", "Hearts")
    ]

    actions = environment.get_actions()

    action_names = [
        action.name
        for action in actions
    ]

    assert "PLAY_CARDS" in action_names
    assert "DISCARD_CARDS" in action_names
    assert "END_ROUND" in action_names


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


def test_simulate_action_does_not_modify_original_state():

    environment = BalatroEnvironment()

    original_state = environment.get_state()

    original_round = original_state.round

    simulated_state = environment.simulate_action(
        BalatroAction(PLAY_CARDS)
    )

    assert original_state.round == original_round
    assert simulated_state.round == original_round + 1


def test_simulate_action_returns_independent_state():

    environment = BalatroEnvironment()

    simulated_state = environment.simulate_action(
        BalatroAction(END_ROUND)
    )

    simulated_state.round = 99

    assert environment.state.round != 99


def test_simulate_discard_changes_hand():

    environment = BalatroEnvironment()

    environment.state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts")
    ]

    simulated = environment.simulate_action(
        BalatroAction(
            DISCARD_CARDS,
            cards=environment.state.hand.copy()
        )
    )

    assert len(simulated.hand) == 2
    assert simulated.discards_remaining == 2
    assert len(environment.state.hand) == 2