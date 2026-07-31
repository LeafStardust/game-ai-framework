from agents.random_agent import RandomAgent
from framework.core.game_runner import GameRunner
from games.dummy.environment import DummyEnvironment


def test_game_runner_completes():

    environment = DummyEnvironment()
    agent = RandomAgent()

    runner = GameRunner(
        environment,
        agent
    )

    reward = runner.run()

    assert reward == 1