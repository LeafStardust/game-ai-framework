from framework.core.action import Action
from framework.core.state import GameState
from framework.evaluation.evaluator import CompositeEvaluator

from games.balatro.heuristics.discard_value import (
    DiscardValueHeuristic
)

from games.balatro.heuristics.play_cards_value import (
    PlayCardsValueHeuristic
)

from games.balatro.heuristics.blind_progress import (
    BlindProgressHeuristic
)

from games.balatro.heuristics.risk import (
    RiskHeuristic
)


class BalatroEvaluator:

    def __init__(self):

        self.evaluator = CompositeEvaluator(
            [
                DiscardValueHeuristic(),
                PlayCardsValueHeuristic(),
                BlindProgressHeuristic(),
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