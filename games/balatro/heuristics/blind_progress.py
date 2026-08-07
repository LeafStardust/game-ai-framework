from framework.core.action import Action
from framework.core.state import GameState

from framework.evaluation.heuristic import Heuristic


class BlindProgressHeuristic(Heuristic):

    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        if state.blind is None:
            return 0.0

        requirement = state.blind.requirement

        if requirement <= 0:
            return 0.0

        progress = state.blind_score / requirement

        score = progress * 100

        if state.blind_score >= requirement:
            score += 500

        return score