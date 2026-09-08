from games.balatro.joker import Joker, JokerContext


class ThrowbackJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "BLIND_SKIPPED":
            self.x_mult += 0.25

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context