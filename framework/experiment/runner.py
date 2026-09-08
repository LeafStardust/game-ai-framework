from framework.agent.agent import Agent
from framework.core.game import Game
from framework.core.game_runner import GameRunner
from framework.experiment.result import ExperimentResult


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
    ) -> ExperimentResult:
        """
        Runs multiple episodes and returns rewards.
        """

        rewards = []
        steps = []

        for _ in range(episodes):

            runner = GameRunner(
                self.game,
                self.agent
            )

            reward = runner.run()

            rewards.append(
                reward
            )

            steps.append(
                len(runner.get_history())
            )

        return ExperimentResult(
            rewards,
            steps
        )