import random

from agents.random_agent import RandomAgent
from framework.core.game_runner import GameRunner
from framework.core.game import Game
from games.dummy.adapter import DummyAdapter


def test_game_runner_completes():

    random.seed(42)

    game = Game(
        DummyAdapter()
    )
    agent = RandomAgent()

    runner = GameRunner(
        game,
        agent
    )

    reward = runner.run()

    assert reward == 1


def test_game_runner_records_experience():

    game = Game(
        DummyAdapter()
    )
    agent = RandomAgent()

    runner = GameRunner(
        game,
        agent
    )

    runner.run()

    history = runner.get_history()

    assert len(history) > 0