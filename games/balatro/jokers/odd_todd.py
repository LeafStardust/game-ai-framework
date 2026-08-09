from games.balatro.joker import Joker, JokerContext


class OddToddJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        odd_ranks = {
            "A",
            "3",
            "5",
            "7",
            "9"
        }

        context.score.chips += sum(
            card.rank in odd_ranks
            for card in context.cards
        ) * 31

        return context