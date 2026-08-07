from framework.core.action import Action
from framework.core.state import GameState
from framework.evaluation.heuristic import Heuristic


class RiskHeuristic(Heuristic):
    """
    Evaluates risk associated with actions.
    """

    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        if action.name == "END_ROUND":
            return -5.0

        return 0.0