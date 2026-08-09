from games.balatro.joker import Joker, JokerContext


class PhotographJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if context.cards and context.cards[0].rank in {"J", "Q", "K"}:
            context.score.x_mult *= 2

        return context