from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class GluttonousJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        mult = sum(
            card.suit == "Clubs"
            for card in cards
        ) * 3

        return HandScore(
            score.chips,
            score.mult + mult
        )