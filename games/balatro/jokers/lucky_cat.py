from games.balatro.joker import Joker, JokerContext


class LuckyCatJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "LUCKY_TRIGGERED":
            self.x_mult += 0.25
            return context

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context
