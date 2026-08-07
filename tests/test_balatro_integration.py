from framework.core.game import Game
from framework.core.game_runner import GameRunner

from games.balatro.adapter import BalatroAdapter
from agents.balatro_agent import BalatroAgent


def test_balatro_agent_runs_in_game_runner():

    game = Game(
        BalatroAdapter()
    )

    agent = BalatroAgent()

    runner = GameRunner(
        game,
        agent
    )

    runner.run()

    history = runner.get_history()

    assert len(history) > 0