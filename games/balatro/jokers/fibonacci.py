from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class FibonacciJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        fibonacci_ranks = {
            "A",
            "2",
            "3",
            "5",
            "8"
        }

        mult = sum(
            card.rank in fibonacci_ranks
            for card in cards
        ) * 8

        return HandScore(
            score.chips,
            score.mult + mult
        )