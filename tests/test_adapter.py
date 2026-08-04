from games.adapter import GameAdapter


def test_adapter_requires_implementation():

    adapter = GameAdapter()

    try:
        adapter.create_environment()
        assert False
    except NotImplementedError:
        assert True


def test_adapter_state_requires_implementation():

    adapter = GameAdapter()

    try:
        adapter.get_state(None)
        assert False
    except NotImplementedError:
        assert True


def test_adapter_actions_requires_implementation():

    adapter = GameAdapter()

    try:
        adapter.get_actions(None)
        assert False
    except NotImplementedError:
        assert True