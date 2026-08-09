from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class CrazyJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        if self._has_straight(cards):
            return HandScore(
                score.chips,
                score.mult + 12
            )

        return score

    @staticmethod
    def _has_straight(cards):

        values = {
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "10": 10,
            "J": 11,
            "Q": 12,
            "K": 13,
            "A": 14
        }

        ranks = {
            values[card.rank]
            for card in cards
        }

        if {14, 2, 3, 4, 5}.issubset(ranks):
            return True

        return any(
            all(
                value + offset in ranks
                for offset in range(5)
            )
            for value in range(2, 11)
        )