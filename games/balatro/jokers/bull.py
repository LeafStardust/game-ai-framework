from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class BullJoker(Joker):
    """
    Adds 2 Mult for every $5 held.
    """

    def apply(
        self,
        state,
        score: HandScore
    ) -> HandScore:

        mult = (state.money // 5) * 2

        return HandScore(
            score.chips,
            score.mult + mult
        )