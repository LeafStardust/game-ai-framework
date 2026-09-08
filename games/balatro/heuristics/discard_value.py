from framework.core.action import Action
from framework.core.state import GameState
from framework.evaluation.heuristic import Heuristic

from games.balatro.hand import PokerHand
from games.balatro.probability import HandProbability


class DiscardValueHeuristic(Heuristic):

    def __init__(self):
        self.probability = HandProbability()

    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:

        if action.name != "DISCARD_CARDS":
            return 0.0

        discarded_cards = getattr(
            action,
            "cards",
            []
        )

        if not discarded_cards:
            return 0.0

        current_hand = self.probability.best_hand(
            state.hand
        )

        strong_hands = {
            PokerHand.STRAIGHT,
            PokerHand.FLUSH,
            PokerHand.FULL_HOUSE,
            PokerHand.FOUR_OF_A_KIND,
            PokerHand.STRAIGHT_FLUSH
        }

        if current_hand in strong_hands:
            return -50.0

        remaining_cards = self.probability.remaining_cards(
            state.deck
        )

        improvement_chance = self.probability.draw_probability(
            len(discarded_cards),
            remaining_cards,
            1
        )

        score = improvement_chance * 20

        if current_hand == PokerHand.HIGH_CARD:
            score += 10

        elif current_hand == PokerHand.PAIR:
            score += 5

        if getattr(
            state,
            "discards_remaining",
            0
        ) <= 1:
            score -= 10

        return score
