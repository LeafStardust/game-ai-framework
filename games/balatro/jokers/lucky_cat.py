from games.balatro.joker import Joker, JokerContext


class LuckyCatJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "LUCKY_TRIGGERED":
            return context

        self.x_mult += 0.2

        if context.score is not None:
            context.score.x_mult *= 1.2

        return context