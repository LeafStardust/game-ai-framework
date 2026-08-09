from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class BullJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        mult = (state.money // 5) * 2

        return HandScore(
            score.chips,
            score.mult + mult
        )