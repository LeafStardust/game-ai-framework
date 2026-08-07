from framework.agent.agent import Agent
from framework.core.game import Game
from framework.core.game_runner import GameRunner


class ExperimentRunner:
    """
    Runs multiple game episodes for an agent.
    """

    def __init__(
        self,
        game: Game,
        agent: Agent
    ):
        self.game = game
        self.agent = agent


    def run(
        self,
        episodes: int
    ) -> list[float]:
        """
        Runs multiple episodes and returns rewards.
        """

        rewards = []

        for _ in range(episodes):

            runner = GameRunner(
                self.game,
                self.agent
            )

            reward = runner.run()

            rewards.append(
                reward
            )

        return rewards