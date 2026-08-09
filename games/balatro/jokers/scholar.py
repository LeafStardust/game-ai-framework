from games.balatro.joker import Joker, JokerContext


class ScholarJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        aces = sum(
            card.rank == "A"
            for card in context.cards
        )

        context.score.chips += aces * 20
        context.score.mult += aces * 4

        return context