from framework.core.action import Action
from framework.core.state import GameState
from framework.evaluation.heuristic import Heuristic

from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.scoring import BalatroScorer


class PlayCardsValueHeuristic(Heuristic):
    """
    Evaluates playing the current cards.
    """

    def __init__(self):
        self.hand_evaluator = HandEvaluator()
        self.scorer = BalatroScorer()


    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        if action.name != "PLAY_CARDS":
            return 0.0


        if not state.hand:
            return 0.0


        poker_hand = self.hand_evaluator.evaluate(
            state.hand
        )


        hand_score = self.scorer.score(
            poker_hand
        )


        return float(
            hand_score.total
        )