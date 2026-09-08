from games.dummy.environment import DummyEnvironment
from games.dummy.actions import INCREASE, DECREASE


def test_environment_initial_state():

    environment = DummyEnvironment()

    state = environment.get_state()

    assert state.value == 0


def test_environment_increase_action():

    environment = DummyEnvironment()

    environment.execute_action(INCREASE)

    assert environment.get_state().value == 1


def test_environment_decrease_action():

    environment = DummyEnvironment()

    environment.execute_action(DECREASE)

    assert environment.get_state().value == -1