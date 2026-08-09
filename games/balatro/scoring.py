from dataclasses import dataclass

from games.balatro.hand import PokerHand
from games.balatro.joker import JokerContext


@dataclass
class HandScore:

    chips: int
    mult: int
    x_mult: float = 1.0

    @property
    def total(self) -> int:
        return int(
            self.chips
            * self.mult
            * self.x_mult
        )


class BalatroScorer:

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
        hand: PokerHand,
        state=None,
        cards=None
    ) -> HandScore:

        base_score = self.SCORES[hand]

        score = HandScore(
            base_score.chips,
            base_score.mult,
            base_score.x_mult
        )

        if state is not None:

            context = JokerContext(
                state=state,
                score=score,
                cards=cards or [],
                held_cards=getattr(state, "hand", []),
                trigger="HAND_SCORED"
            )

            for joker in state.jokers:
                context = joker.apply(context)

            score = context.score

        return score