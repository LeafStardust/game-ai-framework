from framework.core.game import Game
from games.dummy.adapter import DummyAdapter


def test_game_creates_environment():

    game = Game(
        DummyAdapter()
    )

    assert game.environment is not None