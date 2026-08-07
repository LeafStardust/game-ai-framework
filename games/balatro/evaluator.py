from framework.core.action import Action
from framework.core.state import GameState
from framework.evaluation.evaluator import CompositeEvaluator

from games.balatro.heuristics.discard_value import (
    DiscardValueHeuristic
)
from games.balatro.heuristics.hand_value import (
    HandValueHeuristic
)
from games.balatro.heuristics.risk import (
    RiskHeuristic
)


class BalatroEvaluator:
    """
    Balatro-specific evaluator composed from multiple heuristics.
    """

    def __init__(self):

        self.evaluator = CompositeEvaluator(
            [
                DiscardValueHeuristic(),
                HandValueHeuristic(),
                RiskHeuristic()
            ]
        )


    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        return self.evaluator.evaluate(
            state,
            action
        )