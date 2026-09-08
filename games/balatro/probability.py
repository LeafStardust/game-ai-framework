from itertools import combinations

from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator


class HandProbability:

    HAND_VALUES = {
        hand: index
        for index, hand in enumerate(PokerHand)
    }

    def __init__(self):
        self.hand_evaluator = HandEvaluator()

    def remaining_cards(
        self,
        deck: list
    ) -> int:

        return len(deck)

    def draw_probability(
        self,
        desired_cards: int,
        total_cards: int,
        draws: int
    ) -> float:

        if total_cards <= 0:
            return 0.0

        if desired_cards <= 0:
            return 0.0

        return min(
            (desired_cards / total_cards) * draws,
            1.0
        )

    def best_hand(
        self,
        cards: list
    ) -> PokerHand:

        if not cards:
            return PokerHand.HIGH_CARD

        best = PokerHand.HIGH_CARD
        best_value = self.HAND_VALUES[best]
        max_cards = min(5, len(cards))

        for amount in range(1, max_cards + 1):

            for selection in combinations(
                cards,
                amount
            ):
                hand = self.hand_evaluator.evaluate(
                    list(selection)
                )
                value = self.HAND_VALUES[hand]

                if value > best_value:
                    best = hand
                    best_value = value

        return best

    def hand_distribution(
        self,
        states: list
    ) -> dict[PokerHand, float]:

        if not states:
            return {
                hand: 0.0
                for hand in PokerHand
            }

        counts = {
            hand: 0
            for hand in PokerHand
        }

        for state in states:
            counts[self.best_hand(state.hand)] += 1

        return {
            hand: count / len(states)
            for hand, count in counts.items()
        }

    def hand_probability(
        self,
        states: list,
        hand: PokerHand
    ) -> float:

        distribution = self.hand_distribution(
            states
        )

        return distribution[hand]
