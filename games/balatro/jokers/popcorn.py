from games.balatro.joker import Joker, JokerContext


class PopcornJoker(Joker):

    def __init__(self):
        self.mult = 20

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.mult += self.mult

        if context.trigger == "ROUND_ENDED":
            self.mult = max(self.mult - 4, 0)

        return context