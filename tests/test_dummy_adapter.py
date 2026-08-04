from games.dummy.adapter import DummyAdapter


def test_dummy_adapter_creates_environment():

    adapter = DummyAdapter()

    environment = adapter.create_environment()

    assert environment is not None


def test_dummy_adapter_gets_state():

    adapter = DummyAdapter()

    environment = adapter.create_environment()

    state = adapter.get_state(
        environment
    )

    assert state is not None


def test_dummy_adapter_gets_actions():

    adapter = DummyAdapter()

    environment = adapter.create_environment()

    actions = adapter.get_actions(
        environment
    )

    assert len(actions) == 2