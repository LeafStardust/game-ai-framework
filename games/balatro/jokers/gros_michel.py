import random

from games.balatro.joker import Joker, JokerContext


class GrosMichelJoker(Joker):

    def __init__(self):
        self.mult = 15
        self.destroyed = False

    def apply(self, context: JokerContext) -> JokerContext:
        if self.destroyed:
            return context

        if context.score is not None:
            context.score.mult += self.mult

        if context.trigger == "ROUND_ENDED":
            if random.random() < 1 / 6:
                self.destroyed = True
                context.data["destroy_self"] = True

        return context