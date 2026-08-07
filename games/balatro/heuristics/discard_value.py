from framework.core.action import Action
from framework.core.state import GameState
from framework.evaluation.heuristic import Heuristic


class DiscardValueHeuristic(Heuristic):
    """
    Evaluates the value of discarding a hand.
    """

    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        if action.name == "DISCARD_HAND":
            return 1.0

        return 0.0