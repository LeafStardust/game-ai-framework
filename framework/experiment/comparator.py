from framework.agent.agent import Agent
from framework.core.game import Game

from framework.experiment.runner import ExperimentRunner
from framework.experiment.result import ExperimentResult


class Comparator:
    """
    Compares multiple agents through experiments.
    """

    def __init__(
        self,
        game: Game
    ):
        self.game = game


    def compare(
        self,
        agents: list[Agent],
        episodes: int
    ) -> list[ExperimentResult]:
        """
        Runs experiments for each agent.
        """

        results = []

        for agent in agents:

            experiment = ExperimentRunner(
                self.game,
                agent
            )

            result = experiment.run(
                episodes
            )

            results.append(
                result
            )

        return results