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
        scoring_cards = context.data.get("scoring_cards", context.cards)

        context.score.mult += sum(
            card.rank in fibonacci_ranks
            for card in scoring_cards
        ) * 8

        return context
