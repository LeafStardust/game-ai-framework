from framework.core.action import Action
from framework.core.state import GameState
from framework.evaluation.heuristic import Heuristic


class PlayHandValueHeuristic(Heuristic):
    """
    Evaluates playing the current hand.
    """

    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        if action.name == "PLAY_HAND":
            return 10.0

        return 0.0