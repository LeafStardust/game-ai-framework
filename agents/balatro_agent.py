from framework.agent.agent import Agent

from framework.decision.pipeline import DecisionPipeline
from framework.decision.policies.greedy import GreedyPolicy
from framework.decision.search import SearchStrategy

from games.balatro.evaluator import BalatroEvaluator


class BalatroAgent(Agent):
    """
    Balatro agent using heuristic evaluation and search.
    """

    def __init__(self):

        evaluator = BalatroEvaluator()

        super().__init__(
            DecisionPipeline(
                evaluator,
                GreedyPolicy(),
                SearchStrategy(
                    evaluator,
                    None
                )
            )
        )