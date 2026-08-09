from games.balatro.joker import Joker, JokerContext


class FibonacciJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        fibonacci_ranks = {
            "A",
            "2",
            "3",
            "5",
            "8"
        }

        mult = sum(
            card.rank in fibonacci_ranks
            for card in context.cards
        ) * 8

        context.score.mult += mult

        return context