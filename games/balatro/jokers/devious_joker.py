from games.balatro.joker import Joker, JokerContext


class DeviousJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

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
            for card in context.cards
        }

        has_straight = (
            {14, 2, 3, 4, 5}.issubset(ranks)
            or any(
                all(
                    value + offset in ranks
                    for offset in range(5)
                )
                for value in range(2, 11)
            )
        )

        if has_straight:
            context.score.chips += 100

        return context