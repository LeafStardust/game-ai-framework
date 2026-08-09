from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class HalfJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        if len(cards) <= 3:
            return HandScore(
                score.chips,
                score.mult + 20
            )

        return score