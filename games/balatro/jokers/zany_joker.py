from collections import Counter

from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class ZanyJoker(Joker):

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

        if any(count >= 3 for count in counts.values()):
            return HandScore(
                score.chips,
                score.mult + 12
            )

        return score