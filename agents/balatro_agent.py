from framework.agent.agent import Agent

from framework.decision.pipeline import DecisionPipeline
from framework.decision.evaluator import Evaluator
from framework.decision.policy import Policy


class BalatroAgent(Agent):
    """
    Balatro agent using evaluator + policy pipeline.
    """

    def __init__(
        self,
        evaluator: Evaluator,
        policy: Policy
    ):

        super().__init__(
            DecisionPipeline(
                evaluator,
                policy
            )
        )