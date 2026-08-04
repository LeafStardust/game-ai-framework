from framework.core.game import Game
from games.dummy.adapter import DummyAdapter


def test_game_creates_environment():

    adapter = DummyAdapter()

    game = Game(
        adapter
    )

    assert game.environment is not None


def test_game_keeps_adapter():

    adapter = DummyAdapter()

    game = Game(
        adapter
    )

    assert game.adapter is adapter