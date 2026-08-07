from dataclasses import dataclass

from games.balatro.hand import PokerHand


@dataclass
class HandScore:
    """
    Represents a Balatro hand score.
    """

    chips: int
    mult: int

    @property
    def total(self) -> int:
        return self.chips * self.mult


class BalatroScorer:
    """
    Calculates base Balatro hand scores.
    """

    SCORES = {
        PokerHand.HIGH_CARD: HandScore(5, 1),
        PokerHand.PAIR: HandScore(10, 2),
        PokerHand.TWO_PAIR: HandScore(20, 2),
        PokerHand.THREE_OF_A_KIND: HandScore(30, 3),
        PokerHand.STRAIGHT: HandScore(30, 4),
        PokerHand.FLUSH: HandScore(35, 4),
        PokerHand.FULL_HOUSE: HandScore(40, 4),
        PokerHand.FOUR_OF_A_KIND: HandScore(60, 7),
        PokerHand.STRAIGHT_FLUSH: HandScore(100, 8),
    }


    def score(
        self,
        hand: PokerHand
    ) -> HandScore:
        """
        Returns base Balatro score for a poker hand.
        """

        return self.SCORES[hand]