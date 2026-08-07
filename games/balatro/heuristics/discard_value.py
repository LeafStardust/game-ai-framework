from framework.core.action import Action
from framework.core.state import GameState
from framework.evaluation.heuristic import Heuristic

from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand import PokerHand
from games.balatro.probability import HandProbability


class DiscardValueHeuristic(Heuristic):
    """
    Evaluates the value of discarding current cards.
    """

    def __init__(self):
        self.hand_evaluator = HandEvaluator()
        self.probability = HandProbability()


    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        if action.name != "DISCARD_CARDS":
            return 0.0


        if not state.hand:
            return 0.0


        poker_hand = self.hand_evaluator.evaluate(
            state.hand
        )


        strong_hands = {
            PokerHand.STRAIGHT,
            PokerHand.FLUSH,
            PokerHand.FULL_HOUSE,
            PokerHand.FOUR_OF_A_KIND,
            PokerHand.STRAIGHT_FLUSH
        }


        if poker_hand in strong_hands:
            return 0.0


        remaining_cards = self.probability.remaining_cards(
            state.deck_size,
            len(state.hand)
        )

        improvement_chance = self.probability.draw_probability(
            len(getattr(action, "cards", state.hand)),
            remaining_cards,
            1
        )

        return 5.0 + (improvement_chance * 10)