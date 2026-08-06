from framework.agent.agent import Agent

from framework.decision.pipeline import DecisionPipeline
from framework.decision.policies.greedy import GreedyPolicy

from games.balatro.evaluator import BalatroEvaluator


class BalatroAgent(Agent):
    """
    Balatro agent using heuristic evaluation.
    """

    def __init__(self):

        super().__init__(
            DecisionPipeline(
                BalatroEvaluator(),
                GreedyPolicy()
            )
        )