from framework.agent.agent import Agent

from framework.decision.pipeline import DecisionPipeline
from framework.decision.policies.greedy import GreedyPolicy

from games.balatro.evaluator import BalatroEvaluator
from games.balatro.search import BalatroSearchStrategy


class BalatroAgent(Agent):

    def __init__(self):

        evaluator = BalatroEvaluator()

        super().__init__(
            DecisionPipeline(
                evaluator,
                GreedyPolicy(),
                BalatroSearchStrategy(
                    evaluator,
                    None,
                    simulations=8
                )
            )
        )
