from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class EvenStevenJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        even_ranks = {
            "2",
            "4",
            "6",
            "8",
            "10"
        }

        mult = sum(
            card.rank in even_ranks
            for card in cards
        ) * 4

        return HandScore(
            score.chips,
            score.mult + mult
        )