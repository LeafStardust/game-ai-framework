from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class CraftyJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        if cards and len({
            card.suit
            for card in cards
        }) == 1:
            return HandScore(
                score.chips + 80,
                score.mult
            )

        return score