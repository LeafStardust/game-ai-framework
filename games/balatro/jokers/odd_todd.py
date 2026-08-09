from games.balatro.joker import Joker, JokerContext


class OddToddJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        odd_ranks = {
            "A",
            "3",
            "5",
            "7",
            "9"
        }

        chips = sum(
            card.rank in odd_ranks
            for card in context.cards
        ) * 31

        context.score.chips += chips

        return context