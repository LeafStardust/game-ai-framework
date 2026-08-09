from games.balatro.joker import Joker, JokerContext


class BaronJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        kings = sum(
            card.rank == "K"
            for card in context.held_cards
        )

        context.score.x_mult *= 1.5 ** kings

        return context