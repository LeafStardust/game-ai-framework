from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class SlyJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        ranks = [
            card.rank
            for card in cards
        ]

        if len(ranks) != len(set(ranks)):
            return HandScore(
                score.chips + 50,
                score.mult
            )

        return score