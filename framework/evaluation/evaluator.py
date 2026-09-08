from framework.core.action import Action
from framework.core.state import GameState

from framework.evaluation.heuristic import Heuristic


class CompositeEvaluator:
    """
    Combines multiple heuristics into a single score.
    """

    def __init__(
        self,
        heuristics: list[Heuristic]
    ):
        self.heuristics = heuristics


    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        score = 0.0

        for heuristic in self.heuristics:
            score += heuristic.evaluate(
                state,
                action
            )

        return score