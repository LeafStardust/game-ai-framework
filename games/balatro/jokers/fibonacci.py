from games.balatro.joker import Joker, JokerContext


class FibonacciJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        fibonacci_ranks = {
            "A",
            "2",
            "3",
            "5",
            "8"
        }

        context.score.mult += sum(
            card.rank in fibonacci_ranks
            for card in context.cards
        ) * 8

        return context