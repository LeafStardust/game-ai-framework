from games.balatro.joker import Joker, JokerContext


class CrazyJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if self._has_straight(context.cards):
            context.score.mult += 12

        return context

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