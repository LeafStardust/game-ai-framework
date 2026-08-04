from games.balatro.adapter import BalatroAdapter
from games.balatro.environment import BalatroEnvironment


def test_balatro_adapter_creates_environment():

    adapter = BalatroAdapter()

    environment = adapter.create_environment()

    assert isinstance(
        environment,
        BalatroEnvironment
    )


def test_balatro_adapter_gets_state():

    adapter = BalatroAdapter()

    environment = adapter.create_environment()

    state = adapter.get_state(
        environment
    )

    assert state is not None


def test_balatro_adapter_gets_actions():

    adapter = BalatroAdapter()

    environment = adapter.create_environment()

    actions = adapter.get_actions(
        environment
    )

    assert isinstance(
        actions,
        list
    )