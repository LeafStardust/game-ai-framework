from games.adapter import GameAdapter


def test_adapter_requires_implementation():

    adapter = GameAdapter()

    try:
        adapter.create_environment()
        assert False
    except NotImplementedError:
        assert True