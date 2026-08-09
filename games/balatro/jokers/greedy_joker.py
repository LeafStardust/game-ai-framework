from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class GreedyJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        mult = sum(
            card.suit == "Diamonds"
            for card in cards
        ) * 3

        return HandScore(
            score.chips,
            score.mult + mult
        )