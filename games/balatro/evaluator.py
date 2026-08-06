from framework.decision.evaluator import Evaluator
from framework.core.action import Action
from framework.core.state import GameState


class BalatroEvaluator(Evaluator):
    """
    Basic heuristic evaluator for Balatro actions.
    """

    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        if action.name == "PLAY_HAND":
            return 10.0

        if action.name == "DISCARD_HAND":
            return 5.0

        if action.name == "END_ROUND":
            return -10.0

        return 0.0