from collections import Counter

from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class MadJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        counts = Counter(
            card.rank
            for card in cards
        )

        pairs = sum(
            count >= 2
            for count in counts.values()
        )

        if pairs >= 2:
            return HandScore(
                score.chips,
                score.mult + 10
            )

        return score