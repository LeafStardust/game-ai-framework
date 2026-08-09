from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class JollyJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        if self._has_pair(cards):
            return HandScore(
                score.chips,
                score.mult + 8
            )

        return score

    @staticmethod
    def _has_pair(cards):

        ranks = [
            card.rank
            for card in cards
        ]

        return len(ranks) != len(set(ranks))