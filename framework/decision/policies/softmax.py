import math
import random

from framework.core.action import Action
from framework.decision.policy import Policy


class SoftmaxPolicy(Policy):
    """
    Selects actions using softmax probability sampling.
    """

    def __init__(
        self,
        temperature: float = 1.0
    ):
        self.temperature = temperature


    def select_action(
        self,
        actions: list[Action],
        scores: list[float]
    ) -> Action:

        if not actions:
            raise ValueError(
                "No actions available"
            )

        if len(actions) != len(scores):
            raise ValueError(
                "Actions and scores length mismatch"
            )

        scaled_scores = [
            score / self.temperature
            for score in scores
        ]

        max_score = max(scaled_scores)

        exp_scores = [
            math.exp(
                score - max_score
            )
            for score in scaled_scores
        ]

        total = sum(exp_scores)

        probabilities = [
            value / total
            for value in exp_scores
        ]

        return random.choices(
            actions,
            weights=probabilities,
            k=1
        )[0]