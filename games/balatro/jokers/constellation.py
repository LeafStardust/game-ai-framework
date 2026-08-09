from games.balatro.joker import Joker, JokerContext


class ConstellationJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "PLANET_USED":
            self.x_mult += 0.1
            return context

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context