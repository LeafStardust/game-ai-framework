from framework.core.action import Action
from framework.core.state import GameState

from framework.evaluation.heuristic import Heuristic

from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.scoring import BalatroScorer


class BlindProgressHeuristic(Heuristic):

    def __init__(self):

        self.hand_evaluator = HandEvaluator()
        self.scorer = BalatroScorer()


    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        if state.blind is None:
            return 0.0


        if action.name != "PLAY_CARDS":
            return 0.0


        if not action.cards:
            return 0.0


        hand = self.hand_evaluator.evaluate(
            action.cards
        )

        score = self.scorer.score(
            hand
        ).total


        current_progress = state.blind_score

        if current_progress + score >= state.blind.requirement:
            return 1000.0


        return (
            (current_progress + score)
            / state.blind.requirement
        ) * 100