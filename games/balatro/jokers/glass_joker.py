from games.balatro.joker import Joker, JokerContext


class GlassJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        context.score.x_mult *= self.x_mult

        return context
