from games.balatro.joker import Joker, JokerContext


class ConstellationJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "PLANET_USED":
            return context

        self.x_mult += 0.1

        return context