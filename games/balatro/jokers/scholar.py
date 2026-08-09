from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class ScholarJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        aces = sum(
            card.rank == "A"
            for card in cards
        )

        return HandScore(
            score.chips + (aces * 20),
            score.mult + (aces * 4)
        )