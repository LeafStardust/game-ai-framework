from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class OddToddJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        odd_ranks = {
            "A",
            "3",
            "5",
            "7",
            "9"
        }

        chips = sum(
            card.rank in odd_ranks
            for card in cards
        ) * 31

        return HandScore(
            score.chips + chips,
            score.mult
        )