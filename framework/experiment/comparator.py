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
        agents: dict[str, Agent],
        episodes: int
    ) -> dict[str, ExperimentResult]:
        """
        Runs experiments for each agent.
        """

        results = {}

        for name, agent in agents.items():

            experiment = ExperimentRunner(
                self.game,
                agent
            )

            result = experiment.run(
                episodes
            )

            results[name] = result

        return results